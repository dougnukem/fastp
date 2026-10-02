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

Complete public runs on a 48-vCPU (24-core) n2d VM, cold page cache, 2 reps
with alternating order. "master" is upstream 8a2397b; "stack" is #723 plus the
adapter index, memory cap and pull claiming. Raw data: `results/full-2026-09.tsv`.

| dataset | run | reads (M) | read len | fixed stages: master → stack | throughput M/s, stack `-w 8` / `16` / `48` | wall `-w 16`: master → stack |
|---|---|---|---|---|---|---|
| RNA NovaSeq (PE) | SRR10007843 | 31.0 | 150 | 7.2s → 1.2s | 0.30 / 0.55 / 0.42 | 72s → 58s (−20%) |
| WGBS NextSeq (PE) | ERR10308506 | 28.4 | 140 | 30.1s → 18.5s | 0.42 / 0.55 / 0.40 | 85s → 70s (−17%) |
| miRNA HiSeq (SE) | ERR10223911 | 89.2 | 51 | 0.6s → 0.5s | 0.82 / 0.81 / 0.56 | 109s → 111s (+2%) |
| ATAC NextSeq (PE) | ERR10905326 | 42.7 | 151 | 1.3s → 1.3s | 0.41 / 0.55 / 0.43 | 83s → 79s (−5%) |
| RNA HiSeq (SE) | ERR10669429 | 42.6 | 75 | 1.5s → 0.5s | 1.09 / 1.04 / 0.66 | 45s → 42s (−8%) |
| ATAC HiSeq (PE) | SRR891268 | 192.9 | 50 | 1.1s → 0.8s | 0.71 / 0.91 / 0.67 | 232s → 213s (−8%) |

Reads are pairs for PE. Output was byte-identical (decompressed) across both
builds and all thread counts on every dataset. Master deadlocks at `-w 48`
(#721), so that column is the stack only.

- Fixed stages cost the same on a 4M-read subset as on the full run (e.g.
  RNA NovaSeq 7.1s vs 7.2s, WGBS 31.8s vs 30.6s), as the cost model predicts.
- WGBS keeps 18.5s of fixed cost in the stack: bisulfite reads match no known
  adapter, so detection falls through to the seed search, which the 8-mer
  index doesn't cover.
- Every dataset is slower at `-w 48` than at `-w 16` (see profiling below).

## Does a subset predict the full run?

Each full run's wall time predicted from the 4M-read subset of the same run
(30 cells: 6 datasets × 2 builds × `-w 8/16/48`):

| method | median error | worst |
|---|---|---|
| naive: subset wall × N/n | 37% | +241% (WGBS, where fixed cost is large) |
| model: subset fixed + subset processing × N/n | 8% | +39% |

For comparing two builds, the relevant error is on the delta between them:

| method | median error vs measured full-run delta | worst |
|---|---|---|
| raw subset delta | 10.2 points | 25.9 points |
| projected delta | 3.2 points | 10.0 points |

For example, RNA NovaSeq at `-w 8`: the subset shows −27%, the projection −3%,
and the full run measured −7%. The benchmark CI job reports projected numbers
for this reason.

The model overpredicts two datasets (RNA HiSeq SE +22–39%, ATAC HiSeq
+19–28%): their subsets processed 25–40% slower per read than the full runs.
The cause is unexplained: recompressing the subsets at gzip level 1, the first
hypothesis, isn't it (next section). That offset is
the same for both builds, which is why deltas project well even when absolute
times don't.

### A simpler method: fit a line through two subset sizes

A separate scaling experiment (3 complete public runs; subsets of 0.25M, 1M,
4M and 16M pairs; 4 and 16 cores; 4 reps each; one full run per cell) tested
predicting full-run time from `a + b·N` fitted through two subset sizes, using
only wall and CPU time, with no stage timestamps. Median absolute error over
3 datasets × 2 core counts, against the measured full run
(`results/subset-scaling-2026-09.tsv`):

| subset | metric | one size × N/n (16M) | line through 0.25M + 1M | 1M + 4M | 4M + 16M |
|---|---|---|---|---|---|
| first N reads of the original file | wall | 11.0% | 3.9% | 1.9% | 2.0% |
| | CPU | 2.9% | 2.2% | 1.0% | 1.1% |
| first N reads, recompressed (igzip -1) | wall | 19.4% | 5.7% | 3.7% | 7.5% |
| | CPU | 3.4% | 3.3% | 1.1% | 2.3% |
| every k-th read across the file, recompressed | wall | 14.9% | 34.6% | 8.2% | 4.6% |
| | CPU | 3.8% | 5.3% | 3.6% | 2.3% |

- Scaling one subset by N/n overpredicts wall time (up to +47%, WGBS at 16
  cores) because fixed costs are multiplied by N/n. The two-point fit removes that.
- CPU time is predicted better than wall time by every method. First-N subsets
  of 1M and 4M pairs give full-run CPU within 1% (median, worst 7%) and wall
  within 2% (median, worst about 10%).
- Recompressing the subsets moves the median CPU error by about 1 point, so it
  does not explain the overprediction in the previous section.
- Random sampling with a 0.25M subset is unreliable for wall time (worst −179%).

So, for a benchmark on subsets: run two sizes (1M and 4M pairs), take the first
N reads of the original file, and report the intercept (fixed cost) and slope
(CPU-seconds per pair) separately. Three datasets and one full run per cell is
a small sample; treat the error figures as indicative.

The benchmark CI job proposed upstream (`bench.py`) uses this method with 0.3M and 1.2M
pairs, `-w 4`, and gates on projected wall, CPU per pair and peak RSS.

## A code-path model of throughput

Processing throughput is set by whichever resource saturates first:

    throughput ≈ min( reader capacity per mate(L),
                      workers / Σ CPU-µs per read over the active code paths,
                      writer capacity )
    wall ≈ fixed stages + N / throughput

The per-read cost of each code path comes from the on-CPU profile
(`scripts/profile_breakdown.py`); which paths are active depends on options
(adapter trimming by sequence, merge, dedup, polyX, UMI). RNA NovaSeq,
`-w 16`, per read pair:

| code path | CPU-µs per pair (stack) | share |
|---|---|---|
| adapter trim (per read, `Matcher`) | 12.6 | 41% |
| output compression | 6.1 | 20% |
| stats/QC | 4.2 | 14% |
| FASTQ parse | 2.6 | 9% |
| queue/sync (waiting) | 1.4 | 5% |
| overlap analysis, dedup | 2.3 | 8% |
| input decompression | 0.6 | 2% |
| adapter detection | 0.01 | 0% |

Checks against measurement at `-w 16` (measured = processing-stage throughput
of the timed runs):

- RNA NovaSeq, stack: 16 workers / 29 µs of work per pair = 0.55M pairs/s
  predicted; 0.55M/s measured, with 17 of 19 threads saturated. Compute-bound.
- RNA NovaSeq, master: the same 30 µs per pair, but 0.48M/s with workers at
  82%, never saturated. The speedup at `-w 16` comes from the stack keeping
  workers fed, not from detection.
- ATAC HiSeq (50bp), stack: worker ceiling 1.25M/s, measured 0.91M/s with the
  two input readers saturated. Short reads are reader-bound: parsing cost is per
  read, while trimming cost grows with length.

Where the model fails: at `-w 48` on a VM with 24 physical cores it predicted
1.24M/s for RNA NovaSeq and 0.42M/s was measured. Rerunning on 48 physical
cores (below) closes part of the gap (0.72M/s on Intel) but not all of it, and
no case gains more than 6% beyond 24 workers. The counters show it is not memory
traffic (memory-bound is 5–6% of slots at 16 and 48 workers). Keep `-w` at or
below the number of physical cores, and expect no gain past about 24 until the
remaining loss is understood.

To rerun after a code change: profile the new build with `profile_run.sh`, run
`profile_breakdown.py`, and compare per-path costs. A path that got cheaper
raises the worker ceiling only if workers were the saturated resource.

## Estimating runtime for a new dataset

1. Fixed stages: take the value for a similar library type and read length
   from the table above (1–7s typically; up to 30s when no known adapter
   matches and detection falls back to the seed search).
2. Throughput: at `-w 16` on this VM class, about 0.55M pairs/s for 150bp PE
   and 0.9–1.0M reads/s for 50–75bp reads; use the code-path model to adjust for
   options that add or remove work.
3. wall ≈ fixed + N / throughput. For example, 50M pairs of 150bp PE RNA:
   1.2 + 50/0.55 ≈ 92s on the stack at `-w 16`; about 111s on master
   (0.48M/s, 7.2s fixed).

## Profiling a run

`scripts/profile_run.sh` collects, in one run (separate from timing runs):

- **On-CPU:** `perf record` DWARF stacks → flame graph; `perf stat` for IPC,
  cache misses and context switches. Shows which functions consume CPU.
  `profile_breakdown.py` turns the stacks into CPU-µs per read per code path.
- **Per-thread utilisation:** `pidstat -t 1`. The pipeline stage that sits
  at 100% (reader, workers, or writer) is the bottleneck; the others show idle time.
- **Off-CPU:** `offcputime` (BPF) stacks for time spent blocked, such as
  condition-variable waits, backpressure sleeps or I/O. Shows why the idle
  stages are waiting.
- **I/O:** `iostat -x 1`.

Profiled: RNA NovaSeq and ATAC HiSeq, master and stack at `-w 16`, stack at
`-w 48`. Findings:

- Per-read adapter trimming (`Matcher::matchWithOneInsertion` via
  `AdapterTrimmer::trimBySequence`) is the largest cost, 31–43% of CPU in every
  profile. None of the changes so far touch it; it's the biggest remaining target.
- Output compression is second (18–25%), then stats/QC (10–14%).
- Adapter detection is under 1% of CPU on full files.
- Going from `-w 16` to `-w 48` adds 40% CPU with no speedup; queue/sync time
  rises from about 5% to 10–17% (workers waiting).
- Off-CPU stacks were not captured (the BPF capture failed; `profile_run.sh`
  now keeps its stderr in `offcpu.err`).

### 48 physical cores

`c4-standard-96` (Intel Emerald Rapids) and `n2d-highmem-96` (AMD Milan), each
with one thread per core, so 48 vCPUs are 48 physical cores (2 NUMA nodes).
Wall seconds, median of 2 alternating reps, cold page cache
(`results/cores-2026-09.tsv`); the full runs are RNA NovaSeq (31M pairs, 150bp)
and ATAC HiSeq (193M pairs, 50bp):

| machine | build | RNA `-w 16` / `24` / `48` | ATAC `-w 16` / `24` / `48` |
|---|---|---|---|
| Intel C4 | master | 65 / 122 / hangs | 196 / 336 / hangs |
| | stack | 54 / 43 / 44 | 147 / 151 / 176 |
| | stack + gap-search fix | 60 / 48 / 45 | 140 / 150 / 180 |
| AMD n2d | master | 74 / 118 / hangs | 292 / 402 / hangs |
| | stack | 58 / 60 / 66 | 299 / 314 / 373 |
| | stack + gap-search fix | 62 / 59 / 67 | 291 / 307 / 360 |

- Upstream master is 1.4–1.9× slower at `-w 24` than at `-w 16` on both machines
  and both datasets, and hangs at 48. The slowdown starts well below 32 threads.
- With the stack, no case is more than 6% faster at `-w 48` than at `-w 24`, and
  ATAC and AMD RNA are slower at 48 than at 16. CPU seconds at `-w 48` are
  11–39% higher than at 16.
- Absolute times are not comparable across machines: AMD ATAC at `-w 16` took
  299s here and 213s on the earlier 24-core VM. The data disks here were
  restored from snapshots and the machine has two NUMA nodes; neither was
  investigated. Compare builds within one machine.

### Hardware counters (Intel C4, PMU `standard`)

Full RNA NovaSeq (31M pairs), % of pipeline slots (`scripts/profile_pmu.sh`,
`scripts/pmu_breakdown.py`, `results/pmu-2026-09/`):

| run | retiring | bad speculation (branch mispredict) | front-end (latency / bandwidth) | back-end (memory / core) | IPC | branch-miss rate |
|---|---|---|---|---|---|---|
| master `-w 16` | 40.5 | 20.8 (20.3) | 26.2 (8.7 / 17.5) | 12.5 (5.5 / 7.0) | 2.67 | 2.59% |
| stack `-w 16` | 39.9 | 20.5 (20.0) | 27.5 (11.3 / 16.2) | 12.1 (5.2 / 6.9) | 2.65 | 2.83% |
| stack + gap fix `-w 16` | 31.1 | 31.0 (30.7) | 25.9 (11.7 / 14.2) | 12.0 (4.6 / 7.4) | 1.99 | 5.24% |
| stack `-w 48` | 39.1 | 20.4 (19.9) | 26.8 (11.1 / 15.7) | 13.7 (5.9 / 7.8) | 2.58 | 2.90% |

- The workload is branch- and front-end-bound, not memory-bound: back-end is
  12% of slots and memory-bound 5%. Cache, NUMA and bandwidth are not what
  limits it; branchy per-read matching is.
- The two hottest functions are 53% of cycles in the stack.
  `Matcher::matchWithOneInsertion` takes 28% of cycles and 47% of instructions
  at IPC 4.4.
  `CountMismatchesBoundedImpl` (SIMD) takes 25% of cycles and **40% of all branch
  mispredictions** (IPC 1.5, 15.5 mispredictions per 1k instructions).
  `countMismatchesBounded` and `OverlapAnalysis::analyze` add about 12% each at
  about 29 per 1k.
- Master and stack have the same profile (IPC 2.67 vs 2.65): the stack did not
  change the per-read code.
- The gap-search fix with early exit executes **17% fewer instructions** (7.51T
  vs 9.06T) but takes **10% more cycles** (3.77T vs 3.42T): the branch-miss rate
  nearly doubles (2.83% to 5.24%) and `matchWithOneInsertion` drops from IPC 4.4 to 2.0. An
  instruction-count gate would have passed this change while CPU time got worse,
  so gate on CPU seconds.
- `-w 48` vs `-w 16` (stack): cycles rise 3% (3.53T vs 3.42T) but CPU seconds
  rise 32% (864 to 1141, from the timing runs). That is an effective clock of
  about 4.0 GHz falling to 3.1 GHz (cycles ÷ CPU-seconds), so on this VM most of
  the extra CPU time at 48 workers is lower clock speed under all-core load,
  not extra work. This is an estimate: the counter and timing runs are separate,
  and AMD has no counters to confirm it.
- Level-3 cache events are unavailable at `standard`; they need `enhanced`,
  which GCE offers only on 144- and 288-vCPU C4 machines.

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
