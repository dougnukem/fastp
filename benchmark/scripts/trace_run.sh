#!/bin/bash
# Runs a trace build (`make TRACE=1`) over datasets x thread counts x input kinds and writes,
# per cell, the raw trace, trace_analyze.py's report and its JSON (per-read stage costs).
# Also times the same cell with a normal build, if given, to measure trace overhead.
#
# Usage: trace_run.sh <fastp-trace> <data_dir> <work_dir> <out_dir> "<name>:<PE|SE> ..." [threads] [inputs] [fastp-normal]
#   threads comma list; "default" runs without -w. Default: 16,48
#   inputs  comma list of gz (sequencer .gz from data_dir), bgzf, plain (made by io_variants.sh
#           in work_dir). Default: gz
# Output is always .gz (the normal configuration); see io_variants.sh for other output modes.
set -uo pipefail
FT=${1:?usage: trace_run.sh <fastp-trace> <data_dir> <work_dir> <out_dir> "<name:layout ...>" [threads] [inputs] [fastp-normal]}
D=${2:?}; W=${3:?}; O=${4:?}; SPECS=${5:?}
THREADS=${6:-16,48}; INPUTS=${7:-gz}; FN=${8:-}
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$O"; RUN=$(mktemp -d -p "$W"); trap 'rm -rf "$RUN"' EXIT
[ -s "$O/overhead.tsv" ] || echo -e "dataset\tinput\tthreads\tnormal_wall\ttrace_wall" > "$O/overhead.tsv"
for spec in $SPECS; do
  IFS=: read -r name layout <<< "$spec"
  for in in ${INPUTS//,/ }; do
    case $in in
      gz) i1="$D/${name}_R1.fastq.gz"; i2="$D/${name}_R2.fastq.gz" ;;
      bgzf) i1="$W/${name}_R1.bgzf.fastq.gz"; i2="$W/${name}_R2.bgzf.fastq.gz" ;;
      plain) i1="$W/${name}_R1.fastq"; i2="$W/${name}_R2.fastq" ;;
    esac
    [ -s "$i1" ] || { echo "missing $i1 (run io_variants.sh first for bgzf/plain)" >&2; continue; }
    for t in ${THREADS//,/ }; do
      wa=""; [ "$t" != default ] && wa="-w $t"
      if [ "$layout" = PE ]; then args="$wa --detect_adapter_for_pe -i $i1 -I $i2 -o $RUN/o1.fq.gz -O $RUN/o2.fq.gz"
      else args="$wa -i $i1 -o $RUN/o1.fq.gz"; fi
      cell="$name.$in.w$t"
      cat "$i1" $([ "$layout" = PE ] && echo "$i2") > /dev/null
      s=$(date +%s.%N)
      FASTP_TRACE_FILE="$O/$cell.trace.tsv" "$FT" $args -j "$RUN/r.json" -h "$RUN/r.html" 2> "$O/$cell.stderr"
      tw=$(echo "$(date +%s.%N) - $s" | bc)
      nw=-
      if [ -n "$FN" ]; then
        s=$(date +%s.%N); "$FN" $args -j "$RUN/r.json" -h "$RUN/r.html" 2>/dev/null
        nw=$(echo "$(date +%s.%N) - $s" | bc)
      fi
      echo -e "$name\t$in\t$t\t$nw\t$tw" >> "$O/overhead.tsv"
      python3 "$HERE/trace_analyze.py" "$O/$cell.trace.tsv" --json "$O/$cell.json" --png "$O/$cell.png" > "$O/$cell.md"
      gzip -f "$O/$cell.trace.tsv"
      echo "$cell: trace ${tw}s normal ${nw}s -> $(grep -m1 -oE '\*\*[A-Za-z-]+\*\*' "$O/$cell.md" | tail -1)" >&2
    done
  done
done
