#!/bin/bash
# Full-size runs: every build in bin_dir x thread counts x datasets, timed per stage.
# Builds alternate order each rep, and each run starts from a cold page cache when
# DROP_CACHES=1 (needs sudo). The first rep of each cell also records a digest of the
# decompressed output (needs igzip), so builds can be compared for identical output.
#
# Usage: run_full.sh <bin_dir> <data_dir> <out_tsv> "<name>:<PE|SE> ..." [threads] [reps] [timeout_s]
#   bin_dir/  executables named fastp-<build>, e.g. fastp-master, fastp-stack
#   threads   comma list; "default" runs without -w (fastp's own default). Default: 8,16,default
set -uo pipefail
BIN=${1:?usage: run_full.sh <bin_dir> <data_dir> <out_tsv> "<name:layout ...>" [threads] [reps] [timeout_s]}
D=${2:?}; OUT=${3:?}; SPECS=${4:?}
THREADS=${5:-8,16,default}; REPS=${6:-2}; TIMEOUT=${7:-14400}
HERE=$(cd "$(dirname "$0")" && pwd)
BUILDS=$(cd "$BIN" && ls fastp-* | sed 's/^fastp-//')
WORK=$(mktemp -d)

echo -e "build\tdataset\tthreads\trep\tresult\twall\tuser\tsys\tmaxrss_kb\tpre\tdetect\tprocess\tfinalize\treads\tbases\tdigest" > "$OUT"
for spec in $SPECS; do
  IFS=: read -r name layout <<< "$spec"
  for t in ${THREADS//,/ }; do
    for rep in $(seq 1 "$REPS"); do
      order=$BUILDS; [ $((rep % 2)) = 0 ] && order=$(echo "$BUILDS" | tac)
      for b in $order; do
        rm -rf "$WORK"/*; w="$WORK"
        wa=""; [ "$t" != default ] && wa="-w $t"
        if [ "$layout" = PE ]; then
          args="$wa --detect_adapter_for_pe -i $D/${name}_R1.fastq.gz -I $D/${name}_R2.fastq.gz -o $w/o1.fq.gz -O $w/o2.fq.gz"
        else
          args="$wa -i $D/${name}_R1.fastq.gz -o $w/o1.fq.gz"
        fi
        if [ "${DROP_CACHES:-0}" = 1 ]; then sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null; fi
        python3 "$HERE/bench_full.py" "$TIMEOUT" "$([ "$rep" = 1 ] && echo 1 || echo 0)" "$b	$name	$t	$rep" -- \
          "$BIN/fastp-$b" $args -j "$w/r.json" -h "$w/r.html" >> "$OUT"
      done
    done
  done
done
rm -rf "$WORK"
