#!/bin/bash
# Profiles one fastp run: on-CPU stacks, per-thread utilisation, off-CPU (blocked) stacks,
# hardware counters and disk I/O. Run it separately from timing runs; perf adds overhead.
#
# Usage: profile_run.sh <fastp> <data_dir> <name> <PE|SE> <threads> <out_dir>
# Needs: perf, sysstat (pidstat, iostat), bpfcc-tools (offcputime-bpfcc), and
# FlameGraph (https://github.com/brendangregg/FlameGraph) at $FLAMEGRAPH (default /tmp/FlameGraph).
# Outputs in out_dir:
#   stat.txt      perf stat: IPC, cache misses, context switches, page faults
#   flame.svg     on-CPU flame graph (DWARF stacks, 49 Hz)
#   top.txt       hottest symbols per thread
#   threads.txt   per-thread CPU% each second: shows which pipeline stage is saturated
#   offcpu.svg    where threads block (condition variables, sleeps, I/O), 120 s window
#   io.txt        iostat -x 1
set -uo pipefail
FASTP=${1:?usage: profile_run.sh <fastp> <data_dir> <name> <layout> <threads> <out_dir>}
D=${2:?}; name=${3:?}; layout=${4:?}; t=${5:?}; o=${6:?}
FG=${FLAMEGRAPH:-/tmp/FlameGraph}
mkdir -p "$o"; w=$(mktemp -d)
if [ "$layout" = PE ]; then
  args="-w $t --detect_adapter_for_pe -i $D/${name}_R1.fastq.gz -I $D/${name}_R2.fastq.gz -o $w/o1.fq.gz -O $w/o2.fq.gz"
else
  args="-w $t -i $D/${name}_R1.fastq.gz -o $w/o1.fq.gz"
fi
iostat -x 1 > "$o/io.txt" & iop=$!
perf stat -e task-clock,cycles,instructions,cache-references,cache-misses,context-switches,cpu-migrations,page-faults \
  -o "$o/stat.txt" -- perf record -q -F 49 --call-graph dwarf,16384 -o "$o/perf.data" -- \
  "$FASTP" $args -j "$w/r.json" -h "$w/r.html" 2> "$o/fastp.stderr" & sp=$!
sleep 5; pid=$(pgrep -n -x "$(basename "$FASTP" | cut -c1-15)")
pidstat -t -u -p "$pid" 1 > "$o/threads.txt" & pp=$!
(sleep 60; sudo offcputime-bpfcc -f -p "$pid" 120 > "$o/offcpu.txt" 2>/dev/null) & op=$!
wait $sp; wait $op; kill $pp $iop 2>/dev/null
perf report -i "$o/perf.data" --no-children --sort tid,sym --stdio 2>/dev/null | head -150 > "$o/top.txt"
perf script -i "$o/perf.data" 2>/dev/null | "$FG/stackcollapse-perf.pl" > "$o/folded.txt"
"$FG/flamegraph.pl" --title "$(basename "$FASTP") -w $t $name" "$o/folded.txt" > "$o/flame.svg"
"$FG/flamegraph.pl" --title "$(basename "$FASTP") -w $t $name off-CPU" --colors io --countname us "$o/offcpu.txt" > "$o/offcpu.svg" 2>/dev/null
rm -rf "$o/perf.data" "$w"
