# Full-size benchmarks and runtime projection

Benchmarks on read subsets are fast and repeatable, but some of fastp's stages
cost the same no matter how big the input is. On a subset those stages take up
a much larger share of the runtime than they do on a real run, so a speedup in
them looks bigger than it is. This page covers which stages scale with what,
how to project a subset result to a full dataset, and how to profile a run.

## Cost model per stage

| Stage | What it does | Scales with | Bounded by (source) |
|---|---|---|---|
| pre | read-length sample, read-count estimate | O(1) in file size | 1000 reads; ≤512K reads / 79.2M bases (`evaluateReadNum`) |
| adapter detection | known-adapter match, else seed search | O(1) in file size; grows with read length and adapter search cost | ≤256K reads / 39.6M bases per mate (`evalAdapterAndReadNum`) |
| processing | read → trim/filter → compress → write | O(N · L) ÷ effective workers, until decompression, compression or I/O saturates | – |
| finalize | JSON/HTML report | about O(L) (per-position histograms) | – |
| peak memory | duplication table + reads in flight | fixed + threads × pack size × L; not N | – |

N = reads, L = read length. Once a subset holds more reads than the caps, the
fixed stages cost the same on the subset as on the full file, while processing
shrinks by n/N. That is why a speedup in the fixed stages looks bigger on the
subset. Files smaller than the detection cap, such as many amplicon runs, spend
a large share of their real runtime in detection, so the subset result holds for them.

So wall(N) ≈ pre + detect + N / throughput(threads, L, library type) + finalize.

## Measured constants

_Pending: full-size runs of complete public datasets (upstream master vs this
stack at `-w 8`, `-w 16`, default, and `-w 48`), with stage timings, CPU, peak
RSS and output digests._

## Does a subset predict the full run?

_Pending: each full run's time predicted from subset measurements with the model
above, compared with the measured time._

## Estimating runtime for a new dataset

_Pending: worked example from read count, read length and library type._

## Profiling a run

`scripts/profile_run.sh` collects, in one run (separate from timing runs):

- **On-CPU:** `perf record` DWARF stacks → flame graph; `perf stat` for IPC,
  cache misses and context switches. Shows which functions consume CPU.
- **Per-thread utilisation:** `pidstat -t 1`. The pipeline stage that sits
  at 100% (reader, workers, or writer) is the bottleneck; the others show idle time.
- **Off-CPU:** `offcputime` (BPF) stacks for time spent blocked, such as
  condition-variable waits, backpressure sleeps or I/O. Shows why the idle
  stages are waiting.
- **I/O:** `iostat -x 1`.

_Pending: findings for the profiled datasets._

A next step, if the profiles point at stage balance: a trace build that
timestamps each pack at read, claim, process and write, and records queue depth
and in-flight memory over time.

## Running it

```bash
# complete public runs (see the table in the results section for sizes)
bash scripts/fetch_full.sh data/ "rna_nova:SRR10007843:PE wgbs:ERR10308506:PE"
# bin/ holds fastp-<build> executables to compare
DROP_CACHES=1 bash scripts/run_full.sh bin data results/full.tsv "rna_nova:PE wgbs:PE"
bash scripts/profile_run.sh bin/fastp-master data rna_nova PE 16 prof/master-w16
```
