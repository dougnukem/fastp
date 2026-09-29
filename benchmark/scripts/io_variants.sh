#!/bin/bash
# Runs the same fastp binary on the same reads with the codec stages switched on and off,
# so each stage's cost is the difference between two variants (see decompose.py):
#
#   variant       input            output       what it removes vs gz_gz
#   gz_gz         .gz (sequencer)  .gz -z 4     nothing: the normal run
#   gz_gz_z1      .gz              .gz -z 1     some compression effort
#   gz_plain      .gz              .fq          output compression
#   gz_none       .gz              (no -o/-O)   compression + output write (QC/report only)
#   plain_gz      .fq              .gz          input decompression
#   plain_plain   .fq              .fq          both codecs
#   plain_none    .fq              (none)       codecs + write: parse + trim/filter + stats only
#   bgzf_gz       BGZF .gz         .gz          single-thread inflate -> fastp's parallel BGZF reader
#   bgzf_plain    BGZF .gz         .fq
#
# plain_none is the "compute kernel" floor: what a GPU port of the per-read work would be
# replacing. Everything above it is codec/I/O.
#
# Inputs are served from the page cache (pre-read before each run, so disk speed doesn't
# penalise the 3-4x larger uncompressed inputs). Set DROP_CACHES=1 to run cold instead.
# Derived inputs (.fq and BGZF) are made once in work_dir; how long that took is appended to
# <work_dir>/prep.tsv, because a reformulation that needs converted input has to pay for it.
#
# Usage: io_variants.sh <fastp> <data_dir> <work_dir> <out_tsv> "<name>:<PE|SE> ..." [threads] [reps] [variants]
#   threads   comma list, "default" = no -w (default: 16,48)
#   variants  comma list (default: all of the above)
# Per-thread CPU for each run goes to <out_tsv>.threads/<dataset>.<variant>.<threads>.<rep>.json
set -uo pipefail
FASTP=${1:?usage: io_variants.sh <fastp> <data_dir> <work_dir> <out_tsv> "<name:layout ...>" [threads] [reps] [variants]}
D=${2:?}; W=${3:?}; OUT=${4:?}; SPECS=${5:?}
THREADS=${6:-16,48}; REPS=${7:-2}
VARIANTS=${8:-gz_gz,gz_gz_z1,gz_plain,gz_none,plain_gz,plain_plain,plain_none,bgzf_gz,bgzf_plain}
HERE=$(cd "$(dirname "$0")" && pwd)
TIMEOUT=${TIMEOUT:-14400}
mkdir -p "$W" "$OUT.threads"; RUN=$(mktemp -d -p "$W")
trap 'rm -rf "$RUN"' EXIT

prep() { # <label> <dest> -- cmd...   runs cmd > dest once, records cost
  local label=$1 dest=$2; shift 3
  [ -s "$dest" ] && return
  local tf; tf=$(mktemp)
  /usr/bin/time -f "%e %U %S %M" -o "$tf" bash -c "$*" > "$dest.part" && mv "$dest.part" "$dest"
  echo -e "$label\t$(tr ' ' '\t' < "$tf")\t$(stat -c %s "$dest")" >> "$W/prep.tsv"
  rm -f "$tf"
}
[ -s "$W/prep.tsv" ] || echo -e "step\twall\tuser\tsys\tmaxrss_kb\tout_bytes" > "$W/prep.tsv"
[ -s "$OUT" ] || echo -e "variant\tbuild\tdataset\tthreads\trep\tresult\twall\tuser\tsys\tmaxrss_kb\tpre\tdetect\tprocess\tfinalize\treads\tbases\tdigest" > "$OUT"

for spec in $SPECS; do
  IFS=: read -r name layout <<< "$spec"
  mates=1; [ "$layout" = PE ] && mates="1 2"
  for m in $mates; do
    gz="$D/${name}_R$m.fastq.gz"
    prep "$name.R$m.gunzip(igzip,1t)" "$W/${name}_R$m.fastq" -- igzip -dc "$gz"
    prep "$name.R$m.bgzip(-@$(nproc),l4)" "$W/${name}_R$m.bgzf.fastq.gz" -- bgzip -@ "$(nproc)" -l 4 -c "$W/${name}_R$m.fastq"
  done
  for t in ${THREADS//,/ }; do
    for rep in $(seq 1 "$REPS"); do
      for v in ${VARIANTS//,/ }; do
        rm -rf "${RUN:?}"/*
        in=${v%%_*}; out=${v#*_}; lv=4
        [ "$out" = gz_z1 ] && { out=gz; lv=1; }
        case $in in
          gz) i1="$D/${name}_R1.fastq.gz"; i2="$D/${name}_R2.fastq.gz" ;;
          plain) i1="$W/${name}_R1.fastq"; i2="$W/${name}_R2.fastq" ;;
          bgzf) i1="$W/${name}_R1.bgzf.fastq.gz"; i2="$W/${name}_R2.bgzf.fastq.gz" ;;
        esac
        case $out in
          gz) o1="-o $RUN/o1.fq.gz"; o2="-O $RUN/o2.fq.gz" ;;
          plain) o1="-o $RUN/o1.fq"; o2="-O $RUN/o2.fq" ;;
          none) o1=""; o2="" ;;
        esac
        wa=""; [ "$t" != default ] && wa="-w $t"
        if [ "$layout" = PE ]; then args="$wa -z $lv --detect_adapter_for_pe -i $i1 -I $i2 $o1 $o2"
        else args="$wa -z $lv -i $i1 $o1"; fi
        if [ "${DROP_CACHES:-0}" = 1 ]; then sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null
        else cat "$i1" $([ "$layout" = PE ] && echo "$i2") > /dev/null; fi
        FASTP_BENCH_THREADS_JSON="$OUT.threads/$name.$v.$t.$rep.json" \
          python3 "$HERE/bench_full.py" "$TIMEOUT" "$([ "$rep" = 1 ] && echo 1 || echo 0)" \
          "$v	$(basename "$FASTP")	$name	$t	$rep" -- "$FASTP" $args -j "$RUN/r.json" -h "$RUN/r.html" >> "$OUT"
        tail -1 "$OUT" | cut -f1-8 >&2
      done
    done
  done
done
