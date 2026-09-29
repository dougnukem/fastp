#!/bin/bash
# Runs every CPU-side measurement the reformulation cost model needs, on one box:
#   1. codec_baselines.sh   standalone codec MB/s (R1 of each dataset)
#   2. io_variants.sh       fastp with codec stages switched on/off
#   3. trace_run.sh         trace build, gz and BGZF input
#   4. soa_pack             transform costs (index/pack/emit) + CPU kernel, per dataset;
#                           the first dataset's first batch is dumped for gpu_bench.py
#   5. decompose.py         codec/I-O breakdown report
# then prints the reformulation_model.py command per dataset (it needs gpu_bench.py's JSON from
# the GPU box).
#
# Usage: run_reformulation_suite.sh <bin_dir> <data_dir> <work_dir> <results_dir> "<name>:<PE|SE> ..." [threads] [reps]
#   bin_dir has fastp, fastp-trace (make TRACE=1) and soa_pack (benchmark/tools/soa_pack.cpp)
set -uo pipefail
BIN=${1:?usage: run_reformulation_suite.sh <bin_dir> <data_dir> <work_dir> <results_dir> "<name:layout ...>" [threads] [reps]}
D=${2:?}; W=${3:?}; O=${4:?}; SPECS=${5:?}; THREADS=${6:-16,48}; REPS=${7:-2}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$O"
names=$(for s in $SPECS; do echo "${s%%:*}"; done | tr '\n' ' ')
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$O/suite.log" >&2; }

log "codec baselines: $names"
bash "$HERE/codec_baselines.sh" "$D" "$W" "$O/codec.tsv" "$names" "1,4,16,$(nproc)" 2>> "$O/suite.log"
log "io variants: $SPECS x $THREADS x $REPS"
bash "$HERE/io_variants.sh" "$BIN/fastp" "$D" "$W" "$O/io.tsv" "$SPECS" "$THREADS" "$REPS" 2>> "$O/suite.log"
log "traces"
bash "$HERE/trace_run.sh" "$BIN/fastp-trace" "$D" "$W" "$O/trace" "$SPECS" "$THREADS" gz,bgzf "$BIN/fastp" 2>> "$O/suite.log"
first=1
for n in $names; do
  log "soa_pack $n"
  dump=""; [ $first = 1 ] && dump="--dump $O/soa_$n" && first=0
  "$BIN/soa_pack" "$W/${n}_R1.fastq" 1048576 $dump > "$O/soa_$n.json"
done
python3 "$HERE/decompose.py" "$O/io.tsv" "$O/codec.tsv" --prep "$W/prep.tsv" --md "$O/codec-io.md" > /dev/null
log "done. For each dataset, with gpu.json from gpu_bench.py:"
for s in $SPECS; do
  n=${s%%:*}; t=${THREADS##*,}
  echo "python3 $HERE/reformulation_model.py --trace $O/trace/$n.gz.w$t.json --soa $O/soa_$n.json --gpu gpu.json" \
       "--dataset $n --prep $W/prep.tsv --codec $O/codec.tsv --workers $t --vcpus $(nproc) --gz-bytes <input .gz bytes> --qc-speedups 5,20" | tee -a "$O/suite.log"
done
