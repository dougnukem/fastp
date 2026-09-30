#!/bin/bash
# Hardware-counter profile of one fastp run: top-down slots (level 1 and 2), IPC and branch totals,
# and sampled cycles / instructions / branch-misses per function.
#
# Usage: profile_pmu.sh <fastp> <data_dir> <name> <PE|SE> <threads> <out_dir>
# Needs a VM with a PMU: on GCE, C4/C4A/M4 with --performance-monitoring-unit=standard
# (n2d and GitHub-hosted runners expose none). perf 6.x; the L2 top-down events need Intel Golden Cove or newer.
# fastp's own stderr is kept in fastp.stderr; perf's errors in *.err.
set -uo pipefail
FASTP=${1:?usage: profile_pmu.sh <fastp> <data_dir> <name> <layout> <threads> <out_dir>}
D=${2:?}; name=${3:?}; layout=${4:?}; t=${5:?}; o=${6:?}
mkdir -p "$o"
run_args() {  # fresh output dir per run
  w=$(mktemp -d)
  if [ "$layout" = PE ]; then echo "-w $t --detect_adapter_for_pe -i $D/${name}_R1.fastq.gz -I $D/${name}_R2.fastq.gz -o $w/o1.fq.gz -O $w/o2.fq.gz -j $w/r.json -h $w/r.html"
  else echo "-w $t -i $D/${name}_R1.fastq.gz -o $w/o1.fq.gz -j $w/r.json -h $w/r.html"; fi
}
TD="{slots,topdown-retiring,topdown-bad-spec,topdown-fe-bound,topdown-be-bound,topdown-heavy-ops,topdown-br-mispredict,topdown-fetch-lat,topdown-mem-bound}"
perf stat -x, -e "$TD" -o "$o/topdown.csv" -- "$FASTP" $(run_args) 2> "$o/topdown.err" > /dev/null
perf stat -x, -e instructions,cycles,branches,branch-misses -o "$o/totals.csv" -- "$FASTP" $(run_args) 2> "$o/totals.err" > /dev/null
perf record -q -o "$o/perf.data" -e cycles/period=20000003/ -e instructions/period=30000003/ -e branch-misses/period=200003/ \
  -- "$FASTP" $(run_args) 2> "$o/fastp.stderr" > /dev/null
perf report -i "$o/perf.data" --stdio --no-children --sort symbol 2> "$o/report.err" | grep -E "^# Samples|^ +[0-9.]+%" > "$o/report.txt"
rm -f "$o/perf.data"
