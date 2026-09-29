# Per-pack trace build

[codec-io.md](codec-io.md) finds each stage's cost by switching it off and seeing what the
run loses. That's cheap but coarse: it gives differences between runs, and stages overlap.
A trace build measures the stages directly inside one run. It records what every thread is
doing, pack by pack, so you can see which thread is the critical path and what each stage
costs per read.

## What's recorded

`make TRACE=1` builds `./fastp-trace` (from its own `obj-trace/`, so it never mixes with a normal
build and switching needs no `make clean`), with `FASTP_TRACE` defined to turn on `src/fptrace.h`. Each thread appends timed
spans to its own buffer (no locks on the hot path). At exit the buffers are written as TSV to
`$FASTP_TRACE_FILE` (default `fastp.trace.tsv`). Without `TRACE=1` the macros compile to
nothing.

| span | thread | covers | a / b |
|---|---|---|---|
| `read_pack` | reader | first read of a pack → handed to a worker (parsing; contains `decompress`) | reads |
| `decompress` | reader | ISA-L inflate of ordinary gzip into the 8 MB parse buffer | bytes out |
| `bgzf_fetch` | reader | waiting for / copying blocks from the BGZF pool | bytes out |
| `bgzf_block` | BGZF pool | one 64 KB block inflated | bytes out |
| `reader_wait` | reader | backpressure sleep (workers or writers behind) | |
| `process` | worker | one pack (PE: one pack per mate): trim, filter, stats, serialise; contains `compress` etc. | reads |
| `worker_wait` | worker | nothing to consume | |
| `compress` | worker (pwrite mode) or writer | libdeflate gzip | bytes in / out |
| `offset_wait` | worker | waiting for the previous pack's output offset (ordered pwrite) | |
| `write` | worker or writer | `pwrite` / `fwrite` | bytes |

Thread naming is **always on**, not only in trace builds: `fp-read-L`, `fp-read-R`,
`fp-read` (SE), `fp-read-I` (interleaved), `fp-work-N`, `fp-bgzf`, `fp-bgzf-io`, `fp-write`.
It's one `pthread_setname_np` per thread. `top -H`, `pidstat -t`, `perf report --sort comm`,
gdb, and `threadcpu.py` then show CPU per pipeline stage without a trace build.

Checks on this PR (Ubuntu 24.04 container, synthetic PE):
- outputs are byte-identical between the normal and trace builds;
- `fastp test` passes;
- trace overhead is not measurable: median wall 3.82 s normal vs 3.83 s traced over 5
  alternating runs, with a 350 KB trace for 600K pairs.
  `trace_run.sh` records overhead per cell on real data (`overhead.tsv`).

## Analysis

`scripts/trace_analyze.py <trace.tsv> [--json costs.json] [--png timeline.png]` reports:

1. **Time by role**: exclusive seconds per span kind (nested spans are subtracted from their
   parent), plus busy and waiting shares of the processing window. The window starts at the
   first pack a reader hands off; anything before it (detection sampling on the main thread,
   and the evaluator's own BGZF pool for BGZF input) is reported separately.
2. **Per-read CPU cost** of each stage (ns per read) and codec rates (MB/s per thread,
   compression ratio). The JSON holds these for the reformulation cost model.
3. **Timeline**: busy / waiting share per role per time bin, which shows phases (e.g.
   reader-bound at the start, worker-bound later).
4. **Pack backlog**: packs handed to workers but not yet started. Near 0 means workers are
   starved. Pinned at the backpressure limit means the reader is ahead.
5. **Bottleneck verdict**: reader-bound, worker-bound, output-ordering-bound, or mixed.

`scripts/trace_run.sh` runs the trace build over datasets × thread counts × input kinds
(gz / BGZF / plain) and writes the trace, report, JSON, PNG and overhead per cell.

Example (Docker, 4 workers, synthetic 300K pairs, gz→gz): workers 95% busy, readers 40% busy
and 51% waiting, backlog pinned at ~28 packs → **worker-bound**. Per read: decompress 1.6 µs,
parse 0.4 µs, trim/filter/stats 5.8 µs, compress 3.5 µs. This is a 4-thread toy; the
full-size results below are what count.

## Results

Same box, datasets and binary as [codec-io.md](codec-io.md#results). gz→gz output, gz or
BGZF input, `-w 16` and `-w 48`. Reports, JSON and two timeline PNGs are in
[`results/trace-2026-09/`](results/trace-2026-09/). Costs are CPU ns per read (all mates).
"inflate" for BGZF cells is the pool's `bgzf_block` time.

| cell | window s | readers busy | workers busy / waiting | inflate | parse | per-read work | compress | verdict |
|---|---|---|---|---|---|---|---|---|
| atac_hiseq.bgzf.w16 | 185 | 81% | 77% / 23% | 284 | 779 | 4209 | 1664 | Mixed |
| atac_hiseq.bgzf.w48 | 269 | 72% | 20% / 80% | 237 | 996 | 4889 | 1817 | Mixed |
| atac_hiseq.gz.w16 | 189 | 89% | 71% / 29% | 180 | 672 | 3935 | 1570 | Reader-bound |
| atac_hiseq.gz.w48 | 259 | 88% | 21% / 79% | 194 | 967 | 4828 | 1817 | Reader-bound |
| rna_nova.bgzf.w16 | 56 | 48% | 90% / 10% | 567 | 853 | 10082 | 2873 | Worker-bound |
| rna_nova.bgzf.w48 | 52 | 65% | 41% / 59% | 501 | 1082 | 12998 | 3449 | Mixed |
| rna_nova.gz.w16 | 52 | 65% | 91% / 9% | 300 | 783 | 9380 | 2714 | Worker-bound |
| rna_nova.gz.w48 | 50 | 92% | 44% / 56% | 344 | 1103 | 13188 | 3461 | Reader-bound |
| rna_se.bgzf.w16 | 44 | 79% | 48% / 52% | 334 | 812 | 6008 | 1899 | Mixed |
| rna_se.bgzf.w48 | 55 | 69% | 14% / 86% | 268 | 887 | 6477 | 1922 | Mixed |
| rna_se.gz.w16 | 41 | 96% | 46% / 54% | 184 | 751 | 5387 | 1715 | Reader-bound |
| rna_se.gz.w48 | 53 | 87% | 14% / 86% | 194 | 893 | 6369 | 1911 | Reader-bound |
| wgbs.bgzf.w16 | 40 | 68% | 81% / 19% | 476 | 897 | 6190 | 2966 | Worker-bound |
| wgbs.bgzf.w48 | 50 | 61% | 25% / 75% | 427 | 1006 | 7182 | 3217 | Mixed |
| wgbs.gz.w16 | 40 | 91% | 76% / 24% | 286 | 799 | 5699 | 2739 | Reader-bound |
| wgbs.gz.w48 | 48 | 91% | 25% / 74% | 315 | 1001 | 7105 | 3190 | Reader-bound |

Trace overhead (`overhead.tsv`, one normal and one traced run per cell) is within run-to-run
noise: −3% to +5%.

Findings:

1. **With ordinary gzip input, 6 of 8 cells are reader-bound.** The one reader thread per mate
   is 87–96% busy while workers wait 24–86% of the time. At `-w 16` only `rna_nova`
   (150 bp reads, the most per-read work) is worker-bound.
2. **The reader's cost is parsing, not gzip.** Building `Read` objects costs 670–1100 ns per
   read, 3–5× the 180–340 ns of ISA-L inflate. BGZF input moves inflate off the reader but
   leaves the parse, which is why it doesn't help ([codec-io.md](codec-io.md#results)).
3. **At `-w 48` every stage gets 15–40% slower per read**: parse 783 → 1103 ns, per-read
   work 9380 → 13188 ns (rna_nova). The 48 vCPUs are 24 cores with 2 SMT threads each, so
   the serial reader shares a core with a worker. That's the most likely reason `-w 48` is
   slower overall. Workers also spend more time in `offset_wait` (ordered output; 3 s → 99 s
   summed).
4. **Per-read work scales with read length at ~65–80 ns per base**, for SE and PE alike (rna_se SE
   75 bp: 5.4 µs; wgbs PE 90 bp: 5.7 µs; rna_nova PE 150 bp: 9.4 µs). So PE overlap analysis
   isn't what makes it expensive.
5. **What the per-read work is** (`perf-rna_nova-w16-workers.txt`, worker threads, self
   time): `Matcher::matchWithOneInsertion` **33%**, `Stats::statRead` 11%, libdeflate
   compression ~20% (inclusive), `countMismatchesBounded` 10%, duplication `checkPair` 4%,
   PE `OverlapAnalysis` 3%. Adapter search by sequence (`trimBySequence`, inclusive) is
   **36%** of worker CPU.

### `trimBySequence`'s one-gap search doesn't advance through the read

The two one-gap loops in `AdapterTrimmer::trimBySequence` step `pos` through the read but
call `Matcher::matchWithOneInsertion(rdata, adata, ...)` and `(adata, rdata, ...)` without
`+ pos`. The exact-match loop just above correctly passes `rdata + startOffset + pos`. So
every iteration compares the **start of the read** against the adapter, with a shrinking
length. An adapter with a one-base indel is only ever looked for at position 0.
It dates to `eb461d5` (2025-06-02, "support one base insertion/deletion in SE mode adapter
trimming") and is in every release since v0.26.0. No existing issue mentions it.

Adding `+ pos` to both calls on 2M reads (n2d-highmem-48, `-w 16`; `fastp test` passes):

| dataset | adapter-trimmed reads (upstream → fixed) | changed records | user CPU |
|---|---|---|---|
| rna_nova PE (2M pairs) | 85,844 → 86,266 (+0.5%) | ~320 per mate | 50.2 → 71.3 s (+42%) |
| rna_se SE (2M reads) | 92,898 → 93,528 (+0.7%) | ~670 | 14.6 → 18.7 s (+28%) |

Doing the search at every position as intended makes the costliest function in fastp more
expensive still. The fix should come with a faster search: for example, run the gap search only at
positions where the exact-match mismatch count came within the gap budget, or use a bit-parallel
(Myers) or banded approach. On a GPU this O(read × adapter) search would also be the most
compute-dense part of fastp's per-read work.

## Running it

```bash
make && make TRACE=1 && cp fastp fastp-trace bin/
bash scripts/trace_run.sh bin/fastp-trace data work results/trace "rna_nova:PE wgbs:PE rna_se:SE" 16,48 gz,bgzf bin/fastp
```
