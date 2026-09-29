#!/bin/bash
# Standalone codec throughput on one mate of each dataset, outside fastp. These are the
# ceilings fastp's pipeline stages sit under:
#   - fastp decompresses a normal (non-BGZF) .gz with ONE ISA-L thread per input file, in the
#     reader thread, so `igzip -dc` single-thread MB/s is the reader's upper bound.
#   - fastp compresses .gz output with libdeflate in each worker (level -z, default 4), so
#     `libdeflate-gzip -4` single-thread MB/s x workers is the compression upper bound.
#   - rapidgzip / bgzip / pigz show what parallel CPU (de)compression would buy instead.
# All runs read from the page cache (file is pre-read once) and write to /dev/null, so disk
# is out of the picture; see io_variants.sh for the same with fastp in the loop.
#
# Usage: codec_baselines.sh <data_dir> <work_dir> <out_tsv> "<name> ..." [threads_list]
#   data_dir has <name>_R1.fastq.gz; work_dir gets <name>_R1.fastq (uncompressed, reused
#   by io_variants.sh). The cost of making it is logged to <work_dir>/prep.tsv, as io_variants.sh does. threads_list is for the parallel tools (default: 1,4,16,<nproc>).
# Needs: igzip (isal), libdeflate-gzip (libdeflate-tools), pigz, bgzip (tabix), rapidgzip (pip).
# Missing tools are skipped and logged, not fatal.
set -uo pipefail
D=${1:?usage: codec_baselines.sh <data_dir> <work_dir> <out_tsv> "<name ...>" [threads]}
W=${2:?}; OUT=${3:?}; NAMES=${4:?}
N=$(nproc); TL=${5:-1,4,16,$N}
mkdir -p "$W"
have() { command -v "$1" >/dev/null 2>&1 || { echo "skip: $1 not installed" >&2; return 1; }; }
[ -s "$OUT" ] || echo -e "dataset\ttool\top\tthreads\tlevel\tin_bytes\tout_bytes\twall\tuser\tsys\tmaxrss_kb\tuncomp_MBps\tcpu_MBps_per_core" > "$OUT"

# run <dataset> <tool> <op> <threads> <level> <in_file> <uncomp_bytes> -- cmd...  (stdout of cmd is counted, then dropped)
run() {
  local ds=$1 tool=$2 op=$3 t=$4 lv=$5 in=$6 ub=$7; shift 8
  local tf; tf=$(mktemp)
  local ob
  ob=$( { /usr/bin/time -f "%e %U %S %M" -o "$tf" "$@" < "$in" | wc -c; } 2>/dev/null )
  read -r wall user sys rss < "$tf"; rm -f "$tf"
  local inb; inb=$(stat -c %s "$in")
  python3 - "$ds" "$tool" "$op" "$t" "$lv" "$inb" "$ob" "$wall" "$user" "$sys" "$rss" "$ub" >> "$OUT" <<'EOF'
import sys
ds, tool, op, t, lv, inb, ob, wall, user, sys_, rss, ub = sys.argv[1:]
wall, cpu, ub = float(wall), float(user) + float(sys_), int(ub)
print('\t'.join([ds, tool, op, t, lv, inb, ob.strip(), f'{wall:.2f}', user, sys_, rss,
                 f'{ub / 1e6 / wall:.0f}', f'{ub / 1e6 / max(cpu, 1e-9):.0f}']))
EOF
  echo "$ds $tool $op t=$t l=$lv: ${wall}s" >&2
}

for name in $NAMES; do
  gz="$D/${name}_R1.fastq.gz"; plain="$W/${name}_R1.fastq"
  [ -s "$gz" ] || { echo "missing $gz" >&2; continue; }
  if [ ! -s "$plain" ]; then
    [ -s "$W/prep.tsv" ] || echo -e "step\twall\tuser\tsys\tmaxrss_kb\tout_bytes" > "$W/prep.tsv"
    tf=$(mktemp); /usr/bin/time -f "%e %U %S %M" -o "$tf" igzip -dc "$gz" > "$plain.part" && mv "$plain.part" "$plain"
    echo -e "$name.R1.gunzip(igzip,1t)\t$(tr ' ' '\t' < "$tf")\t$(stat -c %s "$plain")" >> "$W/prep.tsv"; rm -f "$tf"
  fi
  ub=$(stat -c %s "$plain")
  cat "$gz" "$plain" > /dev/null   # warm the page cache

  # --- decompression of the sequencer's ordinary single-member gzip ---
  have igzip && run "$name" igzip decompress 1 - "$gz" "$ub" -- igzip -dc
  have pigz && run "$name" pigz decompress 1 - "$gz" "$ub" -- pigz -dc
  # libdeflate-gzip needs a seekable file argument, not stdin
  have libdeflate-gzip && run "$name" libdeflate decompress 1 - "$gz" "$ub" -- libdeflate-gzip -dc "$gz"
  if have rapidgzip; then
    for t in ${TL//,/ }; do run "$name" rapidgzip decompress "$t" - "$gz" "$ub" -- rapidgzip -P "$t" -dc "$gz"; done
  fi

  # --- compression of the uncompressed stream (fastp output ~ this, minus filtered reads) ---
  if have libdeflate-gzip; then
    for lv in 1 4 6; do run "$name" libdeflate compress 1 "$lv" "$plain" "$ub" -- libdeflate-gzip -"$lv" -c "$plain"; done
  fi
  have igzip && run "$name" igzip compress 1 1 "$plain" "$ub" -- igzip -1 -c
  if have pigz; then
    for t in ${TL//,/ }; do run "$name" pigz compress "$t" 4 "$plain" "$ub" -- pigz -4 -p "$t" -c; done
  fi

  # --- BGZF: parallel compression, and fastp's parallel BGZF reader makes it parallel to read ---
  if have bgzip; then
    bg="$W/${name}_R1.bgzf.fastq.gz"
    for t in ${TL//,/ }; do run "$name" bgzip compress "$t" 4 "$plain" "$ub" -- bgzip -@ "$t" -l 4 -c; done
    if [ ! -s "$bg" ]; then
      tf=$(mktemp); /usr/bin/time -f "%e %U %S %M" -o "$tf" bgzip -@ "$N" -l 4 -c "$plain" > "$bg"
      echo -e "$name.R1.bgzip(-@$N,l4)\t$(tr ' ' '\t' < "$tf")\t$(stat -c %s "$bg")" >> "$W/prep.tsv"; rm -f "$tf"
    fi
    for t in ${TL//,/ }; do run "$name" bgzip decompress "$t" - "$bg" "$ub" -- bgzip -@ "$t" -dc; done
    have igzip && run "$name" igzip decompress-bgzf 1 - "$bg" "$ub" -- igzip -dc
  fi
done
if command -v column >/dev/null; then column -t -s $'\t' "$OUT"; else cat "$OUT"; fi
