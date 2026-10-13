#!/bin/bash
# Standalone decode throughput (no fastp) for each variant file, piped to /dev/null. The single-thread
# igzip time on the plain file is the "decode floor" in benchmark/gzip-vs-bgzf-design.md (fastp decodes
# plain gzip with ISA-L); gzip -dc is informational.
# Usage: decode_baseline.sh <data_dir> <out_tsv> [threads_csv] [datasets]
# result: OK | ABSENT (tool not installed, empty wall_s) | EXIT<n> (installed but failed, empty wall_s).
# DROP_CACHE=1 drops the page cache before each timed run, as bench_gzip_vs_bgzf.sh does; cache is
# not_dropped | cold | unknown (drop requested but failed) | - (row did not run).
# No `set -e`: every step is checked explicitly; any failure makes the script exit 1 at the end.
set -uo pipefail
DATA=${1:?usage: decode_baseline.sh <data_dir> <out_tsv> [threads] [datasets]}
OUT=${2:?usage: decode_baseline.sh <data_dir> <out_tsv> [threads] [datasets]}
THREADS=${3:-"1,2,4,8,16"}
DATASETS=${4:-"wgs"}
HERE=$(cd "$(dirname "$0")" && pwd)
FAILS=0
printf 'dataset\tmate\tvariant\ttool\tthreads\tcache\tresult\twall_s\tuncompressed_bytes\n' > "$OUT" || { echo "cannot write $OUT" >&2; exit 1; }
IFS=',' read -ra TLIST <<< "$THREADS"

row() { printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$@" | tee -a "$OUT"; }

# Same semantics as bench_gzip_vs_bgzf.sh drop_cache(); keep the two in sync.
drop_cache() {
  if [ "${DROP_CACHE:-0}" != 1 ]; then echo not_dropped; return; fi
  if sync && echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1; then echo cold; else echo unknown; fi
}

time_cmd() { # ds mate variant tool threads bytes -- cmd...
  local ds=$1 mate=$2 variant=$3 tool=$4 t=$5 bytes=$6; shift 7
  local res ec wall cache
  cache=$(drop_cache)
  res=$(python3 "$HERE/run_timed.py" -- "$@")
  IFS=$'\t' read -r ec wall _ <<< "$res"
  if [ "$ec" = 0 ] && [ -n "$wall" ]; then row "$ds" "$mate" "$variant" "$tool" "$t" "$cache" OK "$wall" "$bytes"
  else
    echo "$tool failed (exit ${ec:-?}) on $ds R$mate $variant threads=$t" >&2
    FAILS=$((FAILS + 1)); row "$ds" "$mate" "$variant" "$tool" "$t" "$cache" "EXIT${ec:-?}" "" "$bytes"
  fi
}

for ds in $DATASETS; do
  for mate in 1 2; do
    for variant in plain bgzf; do
      f="$DATA/${ds}_R${mate}.${variant}.fastq.gz"
      [ -s "$f" ] || { echo "skip $ds R$mate $variant: missing $f" >&2; continue; }
      # untimed byte count, once per file and before any drop, so it never warms a timed run's cache
      bytes=$(gzip -dc "$f" | wc -c | tr -d ' ')
      if ! [ "${bytes:-0}" -gt 0 ] 2>/dev/null; then
        echo "cannot count uncompressed bytes of $f" >&2; FAILS=$((FAILS + 1)); continue
      fi
      time_cmd "$ds" "$mate" "$variant" gzip 1 "$bytes" -- sh -c 'gzip -dc "$1" >/dev/null' _ "$f"
      if command -v igzip >/dev/null; then time_cmd "$ds" "$mate" "$variant" igzip 1 "$bytes" -- sh -c 'igzip -dc "$1" >/dev/null' _ "$f"
      else row "$ds" "$mate" "$variant" igzip 1 - ABSENT "" "$bytes"; fi
      for t in "${TLIST[@]}"; do
        if [ "$variant" = bgzf ]; then # bgzip only reads BGZF
          if command -v bgzip >/dev/null; then time_cmd "$ds" "$mate" "$variant" bgzip "$t" "$bytes" -- sh -c 'bgzip -dc -@ "$1" "$2" >/dev/null' _ "$t" "$f"
          else row "$ds" "$mate" "$variant" bgzip "$t" - ABSENT "" "$bytes"; fi
        fi
        if command -v rapidgzip >/dev/null; then time_cmd "$ds" "$mate" "$variant" rapidgzip "$t" "$bytes" -- sh -c 'rapidgzip -d -c -P "$1" "$2" >/dev/null' _ "$t" "$f"
        else row "$ds" "$mate" "$variant" rapidgzip "$t" - ABSENT "" "$bytes"; fi
      done
    done
  done
done

if [ "$FAILS" -gt 0 ]; then echo "$FAILS run(s) did not complete" >&2; exit 1; fi
