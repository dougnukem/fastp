# gzip vs BGZF decode-cost benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure how much of a fastp run is serial plain-gzip decode and what BGZF input buys end to end, and apply the spec's decision rule.

**Architecture:** A portable timing helper (`run_timed.py`) is shared by a matrix runner (`bench_gzip_vs_bgzf.sh`) and a decode-baseline runner (`decode_baseline.sh`). `make_variants.sh` builds the plain and BGZF inputs from the same reads. `analyze_gzip_vs_bgzf.py` summarizes and applies the decision rule. No fastp source changes.

**Tech Stack:** bash, Python 3 stdlib only (`unittest`), `bgzip` (htslib), optional `igzip` and `rapidgzip`.

**Spec:** `benchmark/gzip-vs-bgzf-design.md`

## Global Constraints

- No change to fastp source, flags or defaults.
- Public accessions only. No Form Bio production data, paths or usage details anywhere in the repo or PR.
- Shell scripts start with `#!/bin/bash` and use `set -uo pipefail` with no `set -e` (as `run_backfill.sh` does), so every failing step must fail loudly: a clear stderr message, a non-OK or `EXIT<n>` row, and a non-zero exit at the end. Test scripts may use `set -e`. They must run on macOS bash 3.2 for smoke tests and on Linux for real runs. No bash 4 features. Guard empty arrays with `${arr[@]+"${arr[@]}"}`.
- Python is stdlib only, tested with `unittest`.
- Results TSV columns, in order: `dataset format mode threads rep bgzf_budget cache result wall_s user_s sys_s max_rss_kb max_thread_cpu_frac reads_after digest`.
- Baseline TSV columns, in order: `dataset mate variant tool threads result wall_s uncompressed_bytes`.
- `format` and `variant` are `plain` or `bgzf`. `mode` is `A`, `B` or `C` as defined in the spec. `result` is `OK`, `HUNG` (any SIGKILL, so an OOM kill is indistinguishable from a timeout), `EXIT<n>`, `NOJSON`, `NODIGEST` or `RUNERR` (results TSV; only `OK` rows are analyzed), or `OK`, `ABSENT`, `EXIT<n>` (baseline TSV).
- Variant files are named `<dataset>_R<1|2>.<plain|bgzf>.fastq.gz`. The `.gz` suffix is required, because fastp counts gz inputs by extension.
- Paired-end only.
- Every commit message ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Push after every commit.

## Review Focus

- One mate missing, empty or truncated: the runner prints `skip ... missing input` and continues; it never records a fake row.
- fastp hangs or deadlocks: recorded as `HUNG` after the timeout, and the sweep continues.
- `igzip` or `rapidgzip` not installed: baseline rows say `ABSENT` with empty `wall_s`; analysis must never treat them as zero.
- Cache state cannot be dropped without root: the `cache` column says `unknown`, never `cold`.
- Output mismatch between plain and BGZF (read counts or digest): `analyze_gzip_vs_bgzf.py` flags it and exits 1.

---

### Task 1: Portable timing helper

**Files:**
- Create: `benchmark/scripts/run_timed.py`
- Test: `benchmark/scripts/test_run_timed.py`

**Interfaces:**
- Produces: `python3 run_timed.py [--timeout S] [--stdout FILE] [--stderr FILE] [--sample-interval S] -- CMD...` prints one tab-separated line `exit<TAB>wall_s<TAB>user_s<TAB>sys_s<TAB>max_rss_kb<TAB>max_thread_cpu_frac`. `exit` is 137 when the timeout kills the process group. `max_thread_cpu_frac` is `NA` off Linux or when the run was shorter than one sample interval.

- [ ] **Step 1: Write the failing test**

```python
# benchmark/scripts/test_run_timed.py
import os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_timed.py")


def run(*args):
    out = subprocess.run([sys.executable, RUN, *args], capture_output=True, text=True, check=True).stdout
    return out.strip().split("\t")


class RunTimedTest(unittest.TestCase):
    def test_exit_code_and_wall(self):
        f = run("--", "sh", "-c", "sleep 0.3; exit 3")
        self.assertEqual(len(f), 6)
        self.assertEqual(f[0], "3")
        self.assertGreaterEqual(float(f[1]), 0.3)

    def test_timeout_kills_and_reports_137(self):
        f = run("--timeout", "0.5", "--", "sleep", "5")
        self.assertEqual(f[0], "137")
        self.assertLess(float(f[1]), 3)

    def test_stdout_redirect(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.txt")
            run("--stdout", p, "--", "echo", "hi")
            self.assertEqual(open(p).read().strip(), "hi")

    def test_max_rss_is_positive_kb(self):
        f = run("--", sys.executable, "-c", "x = bytearray(50_000_000); print(len(x))")
        self.assertGreater(int(f[4]), 40_000)  # KB, so > 40 MB


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 benchmark/scripts/test_run_timed.py -v`
Expected: FAIL (`run_timed.py` does not exist).

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Run a command and print one TSV line: exit, wall_s, user_s, sys_s, max_rss_kb, max_thread_cpu_frac.

Usage: run_timed.py [--timeout S] [--stdout FILE] [--stderr FILE] [--sample-interval S] -- CMD...

exit is 137 if --timeout killed the process group. max_thread_cpu_frac is the busiest sampled
thread's CPU seconds divided by wall time (Linux /proc only; NA elsewhere). It is a lower bound:
threads that exit between samples are missed, which is fine for a reader thread that lives
for the whole run.
"""
import argparse
import os
import signal
import subprocess
import sys
import threading
import time


def thread_cpu(pid):
    """{tid: cpu_seconds} from /proc (Linux). Empty dict if unavailable."""
    out = {}
    try:
        tck = os.sysconf("SC_CLK_TCK")
        for tid in os.listdir(f"/proc/{pid}/task"):
            with open(f"/proc/{pid}/task/{tid}/stat") as f:
                s = f.read()
            fields = s[s.rindex(")") + 2:].split()  # fields[0] is stat field 3 (state)
            out[tid] = (int(fields[11]) + int(fields[12])) / tck  # utime + stime
    except (OSError, ValueError):
        pass
    return out


def main():
    argv = sys.argv[1:]
    i = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=0)
    ap.add_argument("--stdout", default=os.devnull)
    ap.add_argument("--stderr", default=os.devnull)
    ap.add_argument("--sample-interval", type=float, default=0.5)
    args, cmd = ap.parse_args(argv[:i]), argv[i + 1:]

    with open(args.stdout, "wb") as so, open(args.stderr, "wb") as se:
        t0 = time.monotonic()
        p = subprocess.Popen(cmd, stdout=so, stderr=se, start_new_session=True)
        done = threading.Event()
        peak = {}

        def sampler():
            while not done.wait(args.sample_interval):
                for tid, c in thread_cpu(p.pid).items():
                    peak[tid] = max(peak.get(tid, 0.0), c)

        def kill():
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        threading.Thread(target=sampler, daemon=True).start()
        timer = threading.Timer(args.timeout, kill) if args.timeout else None
        if timer:
            timer.start()
        _, status, ru = os.wait4(p.pid, 0)
        wall = time.monotonic() - t0
        done.set()
        if timer:
            timer.cancel()

    code = os.waitstatus_to_exitcode(status)
    if code < 0:
        code = 128 - code
    p.returncode = code
    rss_kb = ru.ru_maxrss // 1024 if sys.platform == "darwin" else ru.ru_maxrss
    frac = f"{max(peak.values()) / wall:.3f}" if peak and wall > 0 else "NA"
    print(f"{code}\t{wall:.3f}\t{ru.ru_utime:.3f}\t{ru.ru_stime:.3f}\t{rss_kb}\t{frac}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 benchmark/scripts/test_run_timed.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add benchmark/scripts/run_timed.py benchmark/scripts/test_run_timed.py
git commit -m "test(bench): portable timing helper with timeout and per-thread CPU sampling

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 2: Variant builder

**Files:**
- Create: `benchmark/scripts/make_variants.sh`
- Test: `benchmark/scripts/test_make_variants.sh`

**Interfaces:**
- Produces: `make_variants.sh <in.fastq.gz> <out_dir> [level=6] [threads=4]` writes `<out_dir>/<base>.plain.fastq.gz` and `<out_dir>/<base>.bgzf.fastq.gz` (`<base>` is the input name without `.fastq.gz`), verifies that both decompress to the same bytes, and prints `variant<TAB>bytes<TAB>level` for each. Existing non-empty outputs are reused.

- [ ] **Step 1: Write the failing test**

```bash
#!/bin/bash
# benchmark/scripts/test_make_variants.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
gzip -c "$ROOT/testdata/R1.fq" > "$T/ds_R1.fastq.gz"

out=$(bash "$HERE/make_variants.sh" "$T/ds_R1.fastq.gz" "$T/v" 6 2)
[ "$(echo "$out" | wc -l | tr -d ' ')" = 2 ] || { echo "expected 2 output lines"; exit 1; }

plain="$T/v/ds_R1.plain.fastq.gz"; bgzf="$T/v/ds_R1.bgzf.fastq.gz"
[ -s "$plain" ] && [ -s "$bgzf" ] || { echo "variant files missing"; exit 1; }

# plain: gzip FLG byte (offset 3) has no FEXTRA, so it is not BGZF
[ "$(xxd -s 3 -l 1 -p "$plain")" = "00" ] || { echo "plain variant has header flags"; exit 1; }
# bgzf: FEXTRA set and subfield id 'BC' at offset 12
[ "$(xxd -s 12 -l 2 -p "$bgzf")" = "4243" ] || { echo "bgzf variant missing BC subfield"; exit 1; }
cmp <(gzip -dc "$plain") "$ROOT/testdata/R1.fq" || { echo "plain content differs"; exit 1; }
cmp <(gzip -dc "$bgzf") "$ROOT/testdata/R1.fq" || { echo "bgzf content differs"; exit 1; }

# second run must reuse files, not rewrite them
before=$(stat -f %m "$plain" 2>/dev/null || stat -c %Y "$plain")
sleep 1; bash "$HERE/make_variants.sh" "$T/ds_R1.fastq.gz" "$T/v" 6 2 >/dev/null
after=$(stat -f %m "$plain" 2>/dev/null || stat -c %Y "$plain")
[ "$before" = "$after" ] || { echo "existing variant was rewritten"; exit 1; }
echo PASS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash benchmark/scripts/test_make_variants.sh`
Expected: FAIL (`make_variants.sh` does not exist).

- [ ] **Step 3: Write minimal implementation**

```bash
#!/bin/bash
# Builds the two inputs the gzip-vs-BGZF benchmark compares, from the SAME reads at the SAME
# compression level: plain gzip (`gzip -L`) and BGZF (`bgzip -l L`). The corpus from
# fetch_corpus.sh is gzip -1, so it is not used directly.
# Usage: make_variants.sh <in.fastq.gz> <out_dir> [level=6] [threads=4]
# Prints "<variant>\t<bytes>\t<level>" per variant.
set -euo pipefail
IN=${1:?usage: make_variants.sh <in.fastq.gz> <out_dir> [level] [threads]}
OUT=${2:?}
LEVEL=${3:-6}
THREADS=${4:-4}
command -v bgzip >/dev/null || { echo "bgzip not found (install htslib)" >&2; exit 1; }
[ -s "$IN" ] || { echo "input missing or empty: $IN" >&2; exit 1; }
mkdir -p "$OUT"
base=$(basename "$IN" .fastq.gz)
plain="$OUT/$base.plain.fastq.gz"
bgzf="$OUT/$base.bgzf.fastq.gz"

# Write to .tmp then rename, so an interrupted run never leaves a truncated "complete" file.
[ -s "$plain" ] || { gzip -dc "$IN" | gzip -"$LEVEL" > "$plain.tmp" && mv "$plain.tmp" "$plain"; }
[ -s "$bgzf" ] || { gzip -dc "$IN" | bgzip -@ "$THREADS" -l "$LEVEL" > "$bgzf.tmp" && mv "$bgzf.tmp" "$bgzf"; }

# Both variants must decode to identical bytes (compare digests, not files, so a 40 GB stream is not held).
a=$(gzip -dc "$plain" | md5sum 2>/dev/null || gzip -dc "$plain" | md5 -q)
b=$(gzip -dc "$bgzf" | md5sum 2>/dev/null || gzip -dc "$bgzf" | md5 -q)
[ "$a" = "$b" ] || { echo "variant contents differ for $IN" >&2; exit 1; }

printf 'plain\t%s\t%s\n' "$(wc -c < "$plain" | tr -d ' ')" "$LEVEL"
printf 'bgzf\t%s\t%s\n' "$(wc -c < "$bgzf" | tr -d ' ')" "$LEVEL"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash benchmark/scripts/test_make_variants.sh`
Expected: `PASS`.

- [ ] **Step 5: Commit**

```bash
git add benchmark/scripts/make_variants.sh benchmark/scripts/test_make_variants.sh
git commit -m "test(bench): build plain-gzip and BGZF variants from the same reads

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 3: Matrix runner

**Files:**
- Create: `benchmark/scripts/bench_gzip_vs_bgzf.sh`
- Test: `benchmark/scripts/test_bench_smoke.sh`

**Interfaces:**
- Consumes: `run_timed.py` (Task 1) and variant files (Task 2).
- Produces: `bench_gzip_vs_bgzf.sh <fastp_bin> <data_dir> <out_tsv> [threads_csv="1,2,4,8,16"] [reps=3] [timeout_s=3600] [datasets="wgs"]`. Writes the results TSV with the columns in Global Constraints. Environment: `DIGEST=1` (default) records a record-level digest for mode C; `DROP_CACHE=1` tries to drop the page cache before each run. `cache` is `not_dropped`, `cold` (drop succeeded) or `unknown` (drop requested but failed).

- [ ] **Step 1: Write the failing test**

```bash
#!/bin/bash
# benchmark/scripts/test_bench_smoke.sh -- needs a fastp binary: FASTP=/path/to/fastp bash test_bench_smoke.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
[ -x "${FASTP:-}" ] || { echo "SKIP: set FASTP to a built fastp binary"; exit 0; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
for m in 1 2; do
  gzip -c "$ROOT/testdata/R$m.fq" > "$T/smoke_R$m.fastq.gz"
  bash "$HERE/make_variants.sh" "$T/smoke_R$m.fastq.gz" "$T/data" 6 2 >/dev/null
done

bash "$HERE/bench_gzip_vs_bgzf.sh" "$FASTP" "$T/data" "$T/out.tsv" "1,2" 1 60 smoke >/dev/null 2>"$T/err.log"

rows=$(($(wc -l < "$T/out.tsv") - 1))
[ "$rows" = 12 ] || { echo "expected 12 rows (2 formats x 3 modes x 2 thread counts), got $rows"; exit 1; }
head -1 "$T/out.tsv" | grep -q $'^dataset\tformat\tmode\tthreads\trep\tbgzf_budget\tcache\tresult\twall_s' || { echo "bad header"; exit 1; }
bad=$(awk -F'\t' 'NR>1 && $8!="OK"' "$T/out.tsv" | wc -l | tr -d ' ')
[ "$bad" = 0 ] || { echo "non-OK rows:"; awk -F'\t' 'NR>1 && $8!="OK"' "$T/out.tsv"; exit 1; }
# both formats must produce the same read count for every (mode, threads)
d=$(awk -F'\t' 'NR>1{print $3,$4,$14}' "$T/out.tsv" | sort -u | awk '{print $1,$2}' | uniq -d | wc -l | tr -d ' ')
[ "$d" = 0 ] || { echo "plain and bgzf disagree on reads_after"; exit 1; }
# missing input is skipped, not recorded
bash "$HERE/bench_gzip_vs_bgzf.sh" "$FASTP" "$T/data" "$T/out2.tsv" "1" 1 60 nosuch >/dev/null 2>"$T/err2.log"
[ "$(($(wc -l < "$T/out2.tsv") - 1))" = 0 ] && grep -q "skip nosuch" "$T/err2.log" || { echo "missing input not skipped"; exit 1; }
echo PASS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `FASTP=/path/to/fastp bash benchmark/scripts/test_bench_smoke.sh`
Expected: FAIL (`bench_gzip_vs_bgzf.sh` does not exist). Without `FASTP`, it prints `SKIP`.

- [ ] **Step 3: Write minimal implementation**

```bash
#!/bin/bash
# Sweeps plain-gzip vs BGZF input x mode (A/B/C) x thread count and records wall time, CPU, RSS,
# busiest-thread CPU fraction, and an output check. See benchmark/gzip-vs-bgzf-design.md.
# Usage: bench_gzip_vs_bgzf.sh <fastp_bin> <data_dir> <out_tsv> [threads_csv] [reps] [timeout_s] [datasets]
# data_dir holds <ds>_R1.<plain|bgzf>.fastq.gz and _R2 (see make_variants.sh).
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

printf 'dataset\tformat\tmode\tthreads\trep\tbgzf_budget\tcache\tresult\twall_s\tuser_s\tsys_s\tmax_rss_kb\tmax_thread_cpu_frac\treads_after\tdigest\n' > "$OUT"

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

run_one() {
  local ds=$1 fmt=$2 mode=$3 t=$4 rep=$5
  local r1="$DATA/${ds}_R1.${fmt}.fastq.gz" r2="$DATA/${ds}_R2.${fmt}.fastq.gz"
  if [ ! -s "$r1" ] || [ ! -s "$r2" ]; then echo "skip $ds/$fmt: missing input ($r1 / $r2)" >&2; return; fi
  local work; work=$(mktemp -d)
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
  if [ "$ec" = 137 ]; then result=HUNG
  elif [ "$ec" != 0 ]; then result="EXIT$ec"
  else
    reads=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["summary"]["after_filtering"]["total_reads"])' "$work/r.json")
    if [ "$mode" = C ] && [ "$DIGEST" = 1 ]; then
      digest=$(for f in "$work/o1.fq.gz" "$work/o2.fq.gz"; do
        gzip -dc "$f" | paste - - - - | LC_ALL=C sort -T "$work" | (md5sum 2>/dev/null || md5 -q) | cut -c1-12
      done | tr '\n' '_')
    fi
  fi
  local budget=-
  [ "$fmt" = bgzf ] && budget=$(bgzf_budget "$t")
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$ds" "$fmt" "$mode" "$t" "$rep" "$budget" "$cache" "$result" "$wall" "$user" "$sys" "$rss" "$frac" "$reads" "$digest" | tee -a "$OUT"
  rm -rf "$work"
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
echo "BENCH DONE" >&2
```

- [ ] **Step 4: Run test to verify it passes**

Run: `FASTP=/path/to/fastp bash benchmark/scripts/test_bench_smoke.sh`
Expected: `PASS`. (Timings from this tiny input are meaningless; the test checks plumbing only.)

- [ ] **Step 5: Commit**

```bash
git add benchmark/scripts/bench_gzip_vs_bgzf.sh benchmark/scripts/test_bench_smoke.sh
git commit -m "test(bench): matrix runner for plain gzip vs BGZF across modes and thread counts

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 4: Decode baselines

**Files:**
- Create: `benchmark/scripts/decode_baseline.sh`
- Modify: `benchmark/scripts/test_bench_smoke.sh` (append the baseline check before the final `echo PASS`)

**Interfaces:**
- Consumes: `run_timed.py` (Task 1), variant files (Task 2).
- Produces: `decode_baseline.sh <data_dir> <out_tsv> [threads_csv="1,2,4,8,16"] [datasets="wgs"]` writes the baseline TSV (columns in Global Constraints). Tools: `gzip -dc` and `igzip -dc` (threads 1), `bgzip -dc -@ N` (BGZF file), `rapidgzip -P N` (both variants). A missing tool gives rows with `result=ABSENT` and empty `wall_s`.

- [ ] **Step 1: Write the failing test** (append to `test_bench_smoke.sh`, before the final `echo PASS`)

```bash
bash "$HERE/decode_baseline.sh" "$T/data" "$T/base.tsv" "1,2" smoke >/dev/null 2>&1
head -1 "$T/base.tsv" | grep -q $'^dataset\tmate\tvariant\ttool\tthreads\tresult\twall_s\tuncompressed_bytes' || { echo "bad baseline header"; exit 1; }
ok=$(awk -F'\t' 'NR>1 && $4=="gzip" && $6=="OK"' "$T/base.tsv" | wc -l | tr -d ' ')
[ "$ok" -ge 2 ] || { echo "gzip baseline rows missing"; exit 1; }
# an absent tool must be ABSENT with an empty wall time, never 0
awk -F'\t' 'NR>1 && $6=="ABSENT" && $7!=""{bad=1} END{exit bad}' "$T/base.tsv" || { echo "ABSENT row has a wall time"; exit 1; }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `FASTP=/path/to/fastp bash benchmark/scripts/test_bench_smoke.sh`
Expected: FAIL (`decode_baseline.sh` does not exist).

- [ ] **Step 3: Write minimal implementation**

```bash
#!/bin/bash
# Standalone decode throughput (no fastp) for each variant file, piped to /dev/null. The single-thread
# plain-gzip numbers are the "decode floor" in benchmark/gzip-vs-bgzf-design.md.
# Usage: decode_baseline.sh <data_dir> <out_tsv> [threads_csv] [datasets]
set -uo pipefail
DATA=${1:?usage: decode_baseline.sh <data_dir> <out_tsv> [threads] [datasets]}
OUT=${2:?}
THREADS=${3:-"1,2,4,8,16"}
DATASETS=${4:-"wgs"}
HERE=$(cd "$(dirname "$0")" && pwd)
printf 'dataset\tmate\tvariant\ttool\tthreads\tresult\twall_s\tuncompressed_bytes\n' > "$OUT"
IFS=',' read -ra TLIST <<< "$THREADS"

row() { printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$@" | tee -a "$OUT"; }

time_cmd() { # ds mate variant tool threads bytes -- cmd...
  local ds=$1 mate=$2 variant=$3 tool=$4 t=$5 bytes=$6; shift 7
  local res ec wall
  res=$(python3 "$HERE/run_timed.py" -- "$@")
  IFS=$'\t' read -r ec wall _ <<< "$res"
  if [ "$ec" = 0 ]; then row "$ds" "$mate" "$variant" "$tool" "$t" OK "$wall" "$bytes"
  else row "$ds" "$mate" "$variant" "$tool" "$t" "EXIT$ec" "" "$bytes"; fi
}

for ds in $DATASETS; do
  for mate in 1 2; do
    for variant in plain bgzf; do
      f="$DATA/${ds}_R${mate}.${variant}.fastq.gz"
      [ -s "$f" ] || { echo "skip $ds R$mate $variant: missing $f" >&2; continue; }
      bytes=$(gzip -dc "$f" | wc -c | tr -d ' ')
      time_cmd "$ds" "$mate" "$variant" gzip 1 "$bytes" -- sh -c 'gzip -dc "$1" >/dev/null' _ "$f"
      for tool in igzip; do
        if command -v $tool >/dev/null; then time_cmd "$ds" "$mate" "$variant" $tool 1 "$bytes" -- sh -c '"$1" -dc "$2" >/dev/null' _ $tool "$f"
        else row "$ds" "$mate" "$variant" $tool 1 ABSENT "" "$bytes"; fi
      done
      for t in "${TLIST[@]}"; do
        if [ "$variant" = bgzf ]; then
          time_cmd "$ds" "$mate" "$variant" bgzip "$t" "$bytes" -- sh -c 'bgzip -dc -@ "$1" "$2" >/dev/null' _ "$t" "$f"
        fi
        if command -v rapidgzip >/dev/null; then
          time_cmd "$ds" "$mate" "$variant" rapidgzip "$t" "$bytes" -- sh -c 'rapidgzip -d -c -P "$1" "$2" >/dev/null' _ "$t" "$f"
        else row "$ds" "$mate" "$variant" rapidgzip "$t" ABSENT "" "$bytes"; fi
      done
    done
  done
done
```

- [ ] **Step 4: Run test to verify it passes**

Run: `FASTP=/path/to/fastp bash benchmark/scripts/test_bench_smoke.sh`
Expected: `PASS`.

- [ ] **Step 5: Commit**

```bash
git add benchmark/scripts/decode_baseline.sh benchmark/scripts/test_bench_smoke.sh
git commit -m "test(bench): standalone decode baselines (gzip, igzip, bgzip, rapidgzip)

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 5: Analysis and decision rule

**Files:**
- Create: `benchmark/scripts/analyze_gzip_vs_bgzf.py`
- Test: `benchmark/scripts/test_analyze_gzip_vs_bgzf.py`

**Interfaces:**
- Consumes: the results TSV (Task 3) and baseline TSV (Task 4), columns as in Global Constraints.
- Produces: `analyze_gzip_vs_bgzf.py <bench.tsv> [baseline.tsv] [--large DATASET]` prints markdown (speedup table per dataset and mode, plain reader-thread CPU fraction, decode floor, verdict). Exit code 1 if any plain-vs-BGZF output mismatch. Importable: `decode_floor(baseline_rows, ds) -> float | None`, `decide(walls, floor, ds) -> (verdict, detail)` where `walls` maps `(dataset, mode, format, threads)` to a list of seconds, and `find_mismatches(bench_rows) -> list`.

- [ ] **Step 1: Write the failing test**

```python
# benchmark/scripts/test_analyze_gzip_vs_bgzf.py
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_gzip_vs_bgzf as a


def bench_row(fmt, wall, t=16, mode="C", reads="100", digest="-", ds="big", result="OK"):
    return dict(dataset=ds, format=fmt, mode=mode, threads=str(t), result=result, wall_s=str(wall),
                max_thread_cpu_frac="0.99", reads_after=reads, digest=digest)


def base_row(mate, wall, variant="plain", tool="gzip", t="1", result="OK", ds="big"):
    return dict(dataset=ds, mate=mate, variant=variant, tool=tool, threads=t, result=result,
                wall_s=str(wall), uncompressed_bytes="1")


class AnalyzeTest(unittest.TestCase):
    def walls(self, plain, bgzf):
        return {("big", "C", "plain", 16): [plain], ("big", "C", "bgzf", 16): [bgzf]}

    def test_floor_is_slower_mate_of_fastest_single_thread_tool(self):
        rows = [base_row("1", 50), base_row("1", 40, tool="igzip"), base_row("2", 45),
                base_row("2", 5, tool="igzip", result="ABSENT")]  # ABSENT must be ignored
        self.assertEqual(a.decode_floor(rows, "big"), 45.0)

    def test_floor_none_without_data(self):
        self.assertIsNone(a.decode_floor([], "big"))

    def test_propose_when_decode_bound_and_bgzf_helps(self):
        verdict, _ = a.decide(self.walls(60, 20), 50.0, "big")
        self.assertTrue(verdict.startswith("PROPOSE"))

    def test_do_not_propose_when_not_decode_bound(self):
        verdict, _ = a.decide(self.walls(60, 20), 20.0, "big")
        self.assertTrue(verdict.startswith("DO NOT PROPOSE"))

    def test_do_not_propose_when_bgzf_does_not_help(self):
        verdict, _ = a.decide(self.walls(60, 50), 55.0, "big")
        self.assertTrue(verdict.startswith("DO NOT PROPOSE"))

    def test_inconclusive_when_data_missing(self):
        verdict, _ = a.decide({("big", "C", "plain", 16): [60]}, 50.0, "big")
        self.assertTrue(verdict.startswith("INCONCLUSIVE"))
        verdict, _ = a.decide(self.walls(60, 20), None, "big")
        self.assertTrue(verdict.startswith("INCONCLUSIVE"))

    def test_mismatch_detected_across_formats(self):
        rows = [bench_row("plain", 10, reads="100"), bench_row("bgzf", 5, reads="99")]
        self.assertEqual(len(a.find_mismatches(rows)), 1)
        rows = [bench_row("plain", 10, digest="aa"), bench_row("bgzf", 5, digest="bb")]
        self.assertEqual(len(a.find_mismatches(rows)), 1)
        rows = [bench_row("plain", 10), bench_row("bgzf", 5)]
        self.assertEqual(a.find_mismatches(rows), [])

    def test_failed_runs_are_not_compared(self):
        rows = [bench_row("plain", 10, reads="100"), bench_row("bgzf", 0, reads="-", result="HUNG")]
        self.assertEqual(a.find_mismatches(rows), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 benchmark/scripts/test_analyze_gzip_vs_bgzf.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Summarize the gzip-vs-BGZF benchmark and apply the decision rule from
benchmark/gzip-vs-bgzf-design.md.

Usage: analyze_gzip_vs_bgzf.py <bench.tsv> [baseline.tsv] [--large DATASET]
Exit status 1 if plain and BGZF runs disagree on output (reads_after or digest).
"""
import argparse
import csv
import statistics
import sys
from collections import defaultdict

DECODE_BOUND_SLACK = 1.30  # plain wall within 30% of the single-thread decode floor
MIN_BGZF_SPEEDUP = 1.5
RULE_MODE, RULE_THREADS = "C", 16


def med(xs):
    return statistics.median(xs) if xs else None


def load(path):
    with open(path) as f:
        return list(csv.DictReader(f, delimiter="\t"))


def decode_floor(baseline, ds):
    """Slower mate's fastest single-thread plain-gzip decode time (PE runs one reader per mate)."""
    per_mate = defaultdict(list)
    for r in baseline:
        if (r["dataset"] == ds and r["variant"] == "plain" and r["threads"] == "1"
                and r["result"] == "OK" and r["wall_s"]):
            per_mate[r["mate"]].append(float(r["wall_s"]))
    if not per_mate:
        return None
    return max(min(v) for v in per_mate.values())


def decide(walls, floor, ds):
    plain = med(walls.get((ds, RULE_MODE, "plain", RULE_THREADS), []))
    bgzf = med(walls.get((ds, RULE_MODE, "bgzf", RULE_THREADS), []))
    if plain is None or bgzf is None or floor is None:
        return ("INCONCLUSIVE: missing plain, BGZF or decode-floor data "
                f"for mode {RULE_MODE} at -w {RULE_THREADS}", "")
    bound = plain <= floor * DECODE_BOUND_SLACK
    gain = plain / bgzf
    detail = (f"plain {plain:.1f}s, BGZF {bgzf:.1f}s ({gain:.2f}x), decode floor {floor:.1f}s "
              f"(plain/floor {plain / floor:.2f}; decode-bound means <= {DECODE_BOUND_SLACK:.2f})")
    if bound and gain >= MIN_BGZF_SPEEDUP:
        return ("PROPOSE a plain-gzip parallel reader upstream", detail)
    return ("DO NOT PROPOSE a reader; recommend BGZF on ingest", detail)


def find_mismatches(bench):
    """(dataset, mode, threads, field, values) where plain and BGZF disagree. Failed runs are skipped."""
    seen = defaultdict(lambda: defaultdict(set))
    for r in bench:
        if r["result"] != "OK":
            continue
        g = (r["dataset"], r["mode"], int(r["threads"]))
        seen[g]["reads_after"].add(r["reads_after"])
        if r["digest"] not in ("", "-"):
            seen[g]["digest"].add(r["digest"])
    return [(*g, field, vals) for g, fields in seen.items() for field, vals in fields.items() if len(vals) > 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bench")
    ap.add_argument("baseline", nargs="?")
    ap.add_argument("--large", help="dataset the decision rule is evaluated on")
    args = ap.parse_args()

    bench = load(args.bench)
    baseline = load(args.baseline) if args.baseline else []
    walls, fracs = defaultdict(list), defaultdict(list)
    for r in bench:
        if r["result"] == "OK":
            k = (r["dataset"], r["mode"], r["format"], int(r["threads"]))
            walls[k].append(float(r["wall_s"]))
            if r["max_thread_cpu_frac"] not in ("", "NA"):
                fracs[k].append(float(r["max_thread_cpu_frac"]))

    for ds in sorted({k[0] for k in walls}):
        floor = decode_floor(baseline, ds)
        print(f"## {ds}\n")
        print("Single-thread decode floor: " + (f"{floor:.1f}s" if floor else "not measured") + "\n")
        for mode in sorted({k[1] for k in walls if k[0] == ds}):
            print(f"### mode {mode}\n")
            print("| -w | plain s | BGZF s | BGZF speedup | plain busiest-thread CPU | plain / floor |")
            print("|---|---|---|---|---|---|")
            for t in sorted({k[3] for k in walls if k[:2] == (ds, mode)}):
                p = med(walls.get((ds, mode, "plain", t), []))
                b = med(walls.get((ds, mode, "bgzf", t), []))
                fr = med(fracs.get((ds, mode, "plain", t), []))
                cell = lambda v, f: f.format(v) if v is not None else "-"
                print(f"| {t} | {cell(p, '{:.1f}')} | {cell(b, '{:.1f}')} | "
                      f"{cell(p / b if p and b else None, '{:.2f}x')} | {cell(fr, '{:.2f}')} | "
                      f"{cell(p / floor if p and floor else None, '{:.2f}')} |")
            print()

    if args.large:
        verdict, detail = decide(walls, decode_floor(baseline, args.large), args.large)
        print(f"## Decision ({args.large})\n\n**{verdict}**\n\n{detail}\n")

    mism = find_mismatches(bench)
    print("## Output agreement between plain and BGZF\n")
    if mism:
        print("**MISMATCHES FOUND:**\n")
        for m in mism:
            print(f"- {m}")
        sys.exit(1)
    print("No mismatches.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 benchmark/scripts/test_analyze_gzip_vs_bgzf.py -v`
Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add benchmark/scripts/analyze_gzip_vs_bgzf.py benchmark/scripts/test_analyze_gzip_vs_bgzf.py
git commit -m "test(bench): summarize gzip vs BGZF results and apply the decision rule

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 6: Real runs, results and recommendation

**Files:**
- Modify: `benchmark/scripts/fetch_corpus.sh` (optional dataset list as 3rd argument)
- Create: `benchmark/results/gzip-vs-bgzf-<date>.tsv`, `benchmark/results/gzip-vs-bgzf-baseline-<date>.tsv`, `benchmark/results/gzip-vs-bgzf-<date>-summary.md`
- Modify: `benchmark/README.md` (short "gzip vs BGZF" section), PR #16 description

**Interfaces:**
- Consumes: everything above, plus a Linux box with 48 vCPUs, local SSD and fastp built from the branch head.

- [ ] **Step 1: Confirm with Doug before creating any VM.** Ask which GCP project and machine to use and whether the cost is acceptable. The earlier backfill used an n2d-highmem-48. Do not create it without an answer.

- [ ] **Step 2: Check that the accession is big enough for the large case.** Large means about 10 GB `.gz` per mate at level 6, roughly 37 GB uncompressed, which is roughly 90M read pairs of 148 bp. Run:

```bash
curl -s "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=SRR952827&result=read_run&fields=read_count,fastq_bytes&format=tsv"
```

If `read_count` is below the pairs needed, pick another verified public accession (or concatenate distinct runs of the same sample). Record the choice in `corpus.md`. Never replicate reads.

- [ ] **Step 3: Add the dataset-list argument to `fetch_corpus.sh`.** Change the last three lines to read the third argument (default `"atac wgs"`) and call `fetch` only for the names listed, so a large `wgs` fetch does not also download `atac`. Run `bash -n benchmark/scripts/fetch_corpus.sh`, then fetch on the VM:

```bash
bash benchmark/scripts/fetch_corpus.sh data/medium 4000000 wgs
bash benchmark/scripts/fetch_corpus.sh data/large <pairs from Step 2> wgs
```

- [ ] **Step 4: Build variants and fastp on the VM.**

```bash
for size in medium large; do for m in 1 2; do
  bash benchmark/scripts/make_variants.sh data/$size/wgs_R$m.fastq.gz variants/$size 6 16
done; done | tee results/variant-sizes.tsv
make -j"$(nproc)"          # fastp binary at the repo root; needs isa-l and libdeflate dev packages
```

Install `igzip` (isa-l) and `rapidgzip` (pip) on the VM so those baselines are not `ABSENT`.

- [ ] **Step 5: Run the benchmarks.**

```bash
DROP_CACHE=1 bash benchmark/scripts/bench_gzip_vs_bgzf.sh ./fastp variants/medium results/gzip-vs-bgzf-medium.tsv "1,2,4,8,16,32" 3 3600 wgs
DIGEST=0 DROP_CACHE=1 bash benchmark/scripts/bench_gzip_vs_bgzf.sh ./fastp variants/large results/gzip-vs-bgzf-large.tsv "1,4,8,16,32" 3 7200 wgs
bash benchmark/scripts/decode_baseline.sh variants/medium results/baseline-medium.tsv "1,2,4,8,16,32" wgs
bash benchmark/scripts/decode_baseline.sh variants/large results/baseline-large.tsv "1,4,8,16,32" wgs
```

The large run skips the record digest, because sorting about 37 GB per mate is impractical. The `reads_after` check still runs. If a run reports `unknown` in the `cache` column, say so in the summary and do not call it cold.

- [ ] **Step 6: Analyze and verify by direct check.**

```bash
python3 benchmark/scripts/analyze_gzip_vs_bgzf.py results/gzip-vs-bgzf-large.tsv results/baseline-large.tsv --large wgs > results/gzip-vs-bgzf-<date>-summary.md
```

Read the summary and spot-check three TSV rows by hand (for example rerun one fastp command and compare wall time). If a reader thread is not near 100% CPU at the `-w` where plain gzip stops scaling, take a thread dump (`pstack` or `top -H`) before naming a cause.

- [ ] **Step 7: Write the recommendation into the PR.** Copy the verdict and both tables into the PR description with their caveats (cache state, single machine, one accession). Add a short section to `benchmark/README.md`. Delete the VM. Commit and push, then update the PR checklist.

```bash
git add benchmark
git commit -m "docs(bench): gzip vs BGZF results and recommendation

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
git push
```
