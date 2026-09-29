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

_Pending: n2d-highmem-48, full-size datasets, `-w 16` and `-w 48`, gz and BGZF input._

## Running it

```bash
make && make TRACE=1 && cp fastp fastp-trace bin/
bash scripts/trace_run.sh bin/fastp-trace data work results/trace "rna_nova:PE wgbs:PE rna_se:SE" 16,48 gz,bgzf bin/fastp
```
