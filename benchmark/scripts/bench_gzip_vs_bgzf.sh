#!/bin/bash
# Sweeps plain-gzip vs BGZF input x mode (A/B/C) x thread count and records wall time, CPU, RSS,
# busiest-thread CPU fraction, and an output check. See benchmark/gzip-vs-bgzf-design.md.
# Usage: bench_gzip_vs_bgzf.sh <fastp_bin> <data_dir> <out_tsv> [threads_csv] [reps] [timeout_s] [datasets]
# data_dir holds <ds>_R1.<plain|bgzf>.fastq.gz and _R2 (see make_variants.sh).
# Environment: DIGEST=1 (default) digests mode-C output; DROP_CACHE=1 drops the page cache before each run;
# SCRATCH_DIR holds the per-run work dirs (mode C writes GBs of .gz output; digest sorts spill there).
# Default $(dirname out_tsv)/.scratch, not $TMPDIR, which is often a small boot disk; put it on local SSD.
# A scratch dir this script creates is removed at exit if empty.
# No `set -e`: every step is checked explicitly so failures name the step.
set -uo pipefail
FASTP=${1:?usage: bench_gzip_vs_bgzf.sh <fastp_bin> <data_dir> <out_tsv> [threads] [reps] [timeout_s] [datasets]}
DATA=${2:?}
OUT=${3:?}
THREADS=${4:-"1,2,4,8,16"}
REPS=${5:-3}
TIMEOUT=${6:-3600}
DATASETS=${7:-"wgs"}
DIGEST=${DIGEST:-1}
HERE=$(cd "$(dirname "$0")" && pwd)
CPUS=$(getconf _NPROCESSORS_ONLN)

[ -x "$FASTP" ] || { echo "fastp binary not executable: $FASTP" >&2; exit 1; }
[ -d "$DATA" ] || { echo "data dir missing: $DATA" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }
# Pick the hash tool once.
if command -v md5sum >/dev/null; then HASH=md5sum; elif command -v md5 >/dev/null; then HASH="md5 -q"
else echo "need md5sum or md5" >&2; exit 1; fi

SCRATCH=${SCRATCH_DIR:-$(dirname "$OUT")/.scratch}
SCRATCH_MADE=0
[ -d "$SCRATCH" ] || SCRATCH_MADE=1
mkdir -p "$SCRATCH" || { echo "cannot create scratch dir $SCRATCH" >&2; exit 1; }

FAILS=0
WORK=
# Remove the in-flight work dir (GBs of gz output in mode C) on exit or interrupt.
trap '[ -n "$WORK" ] && rm -rf "$WORK"; [ "$SCRATCH_MADE" = 1 ] && rmdir "$SCRATCH" 2>/dev/null' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'dataset\tformat\tmode\tthreads\trep\tbgzf_budget\tcache\tresult\twall_s\tuser_s\tsys_s\tmax_rss_kb\tmax_thread_cpu_frac\treads_after\tdigest\n' > "$OUT" \
  || { echo "cannot write $OUT" >&2; exit 1; }

# A: reader + minimal work. B: default processing, no output. C: default processing + gz output.
mode_flags() {
  case $1 in
    A) echo "-A -G -Q -L --dont_eval_duplication" ;;
    *) echo "--detect_adapter_for_pe" ;;
  esac
}

# Mirrors peprocessor.cpp: max(1, (cpus - (workers + 4)) / gz_inputs), 2 gz inputs.
bgzf_budget() {
  local b=$(( (CPUS - ($1 + 4)) / 2 ))
  [ "$b" -lt 1 ] && b=1
  echo "$b"
}

drop_cache() {
  if [ "${DROP_CACHE:-0}" != 1 ]; then echo not_dropped; return; fi
  if sync && echo 3 | sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1; then echo cold; else echo unknown; fi
}

# Record-level digest of one gz FASTQ (order-independent); empty output means failure.
digest_one() {
  local d
  d=$(gzip -dc "$1" | paste - - - - | LC_ALL=C sort -T "$2" | $HASH | cut -c1-12) || return 1
  [ -n "$d" ] && echo "$d"
}

run_one() {
  local ds=$1 fmt=$2 mode=$3 t=$4 rep=$5
  local r1="$DATA/${ds}_R1.${fmt}.fastq.gz" r2="$DATA/${ds}_R2.${fmt}.fastq.gz"
  if [ ! -s "$r1" ] || [ ! -s "$r2" ]; then echo "skip $ds/$fmt: missing input ($r1 / $r2)" >&2; return; fi
  local work; work=$(mktemp -d "$SCRATCH/run.XXXXXX") || { echo "mktemp failed" >&2; FAILS=$((FAILS + 1)); return; }
  WORK=$work
  local outargs=()
  [ "$mode" = C ] && outargs=(-o "$work/o1.fq.gz" -O "$work/o2.fq.gz")
  local cache; cache=$(drop_cache)
  local res
  # shellcheck disable=SC2046
  res=$(python3 "$HERE/run_timed.py" --timeout "$TIMEOUT" --stdout "$work/out.log" --stderr "$work/err.log" -- \
    "$FASTP" -w "$t" $(mode_flags "$mode") -i "$r1" -I "$r2" ${outargs[@]+"${outargs[@]}"} \
    -j "$work/r.json" -h "$work/r.html")
  local ec wall user sys rss frac
  IFS=$'\t' read -r ec wall user sys rss frac <<< "$res"
  local result=OK reads=- digest=-
  if [ -z "$ec" ] || [ -z "$frac" ]; then
    echo "run_timed.py gave no usable result for $ds/$fmt/$mode/w$t/rep$rep: '$res'" >&2
    result=RUNERR; wall=; user=; sys=; rss=; frac=
  elif [ "$ec" = 137 ]; then result=HUNG
  elif [ "$ec" != 0 ]; then result="EXIT$ec"
  else
    if ! reads=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["summary"]["after_filtering"]["total_reads"])' "$work/r.json"); then
      echo "cannot read reads_after from $work/r.json ($ds/$fmt/$mode/w$t)" >&2; result=NOJSON; reads=-
    elif [ "$mode" = C ] && [ "$DIGEST" = 1 ]; then
      local d1 d2
      # shortcut: each mate is hashed separately, so this cannot detect R1/R2 mispairing.
      if d1=$(digest_one "$work/o1.fq.gz" "$work") && d2=$(digest_one "$work/o2.fq.gz" "$work"); then
        digest="${d1}_${d2}"
      else
        echo "digest failed for $ds/$fmt/$mode/w$t" >&2; result=NODIGEST
      fi
    fi
  fi
  local budget=-
  [ "$fmt" = bgzf ] && budget=$(bgzf_budget "$t")
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$ds" "$fmt" "$mode" "$t" "$rep" "$budget" "$cache" "$result" "$wall" "$user" "$sys" "$rss" "$frac" "$reads" "$digest" | tee -a "$OUT"
  [ "$result" = OK ] || FAILS=$((FAILS + 1))
  rm -rf "$work"; WORK=
}

IFS=',' read -ra TLIST <<< "$THREADS"
for ds in $DATASETS; do
  for t in "${TLIST[@]}"; do
    for mode in A B C; do
      for rep in $(seq 1 "$REPS"); do
        # alternate which format runs first so one format is not always the cache-warm one
        if [ $(( (rep + t) % 2 )) = 0 ]; then order="plain bgzf"; else order="bgzf plain"; fi
        for fmt in $order; do run_one "$ds" "$fmt" "$mode" "$t" "$rep"; done
      done
    done
  done
done
if [ "$FAILS" -gt 0 ]; then echo "$FAILS run(s) did not complete" >&2; exit 1; fi
echo "BENCH DONE" >&2
