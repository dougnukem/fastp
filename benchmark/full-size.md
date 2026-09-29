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
The subsets are the first reads of each run, recompressed at gzip level 1;
the likely cause is that their per-read input cost differs from the original
files, but that isn't confirmed. That offset is
the same for both builds, which is why deltas project well even when absolute
times don't.

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

Where the model fails: at `-w 48` it predicts 1.24M/s for RNA NovaSeq; 0.42M/s
was measured. The VM has 24 physical cores, so 48 workers plus readers and
writers (51 threads) share cores, and CPU per pair rises from 30 to 43 µs.
Even 24 cores would allow 0.79M/s, so there's a further loss this model
doesn't explain. Keep `-w` at or below physical cores minus the reader and
writer threads until that's understood.

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
- Not captured: hardware counters (these VMs expose no PMU, so no IPC or cache
  data) and off-CPU stacks (the BPF capture failed; `profile_run.sh` now keeps
  its stderr in `offcpu.err`).

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
