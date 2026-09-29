# Where the time goes: codecs vs. per-read work

[full-size.md](full-size.md) splits a run by stage in time (pre, detect, processing,
finalize). This page splits the processing stage by *kind of work*: gzip decompression,
FASTQ parsing and per-read QC, gzip compression, and writing. The answer decides which
optimisations can pay off. Speeding up per-read work (SIMD, a GPU port) only helps if
per-read work is on the critical path. If a single decompression thread is, adding
workers or a GPU changes nothing.

## How fastp 1.3.x spends threads on codecs (from the source)

| Stage | Thread(s) | Library | Parallel? |
|---|---|---|---|
| decompress ordinary `.gz` | the reader thread, one per input file | ISA-L `isal_inflate` (`fastqreader.cpp`) | **no**: one thread per mate |
| decompress BGZF `.gz` | `BgzfMtReader` pool, auto-detected from the header | ISA-L, one 64 KB block per task (`bgzf.h`) | yes: `max(1, (nproc − (-w + 4)) / gz_inputs)` threads per reader (`peprocessor.cpp`) |
| parse FASTQ into `Read` objects | the reader thread | – | no |
| trim / filter / stats | `-w` worker threads | – | yes |
| compress `.gz` output | each worker, then `pwrite` at a sequenced offset | libdeflate, level `-z` (default 4) (`writerthread.cpp`) | yes (multi-member gzip) |
| write plain output | one writer thread per output file | – | no |

So compression already scales with workers. Decompression and parsing of a normal
sequencer `.fastq.gz` do not: each mate gets one thread that inflates **and** parses.
That thread's throughput is a ceiling on the whole run, whatever `-w` is.

The BGZF pool is sized from the cores *left over* after workers. On 48 vCPUs, PE input at
`-w 16` gets 14 decompression threads per mate, but at `-w 32` it gets 6 and at `-w 44`
or more it gets 1, the same as ordinary gzip. That is why `io_variants.sh` runs both
a moderate and a high `-w`.

## Method

Two scripts, both reading inputs from the page cache so disk speed isn't measured:

- `scripts/codec_baselines.sh` measures each codec alone (no fastp) in MB/s of
  uncompressed data, per thread count: ISA-L `igzip` (what fastp's reader uses), libdeflate
  (what fastp's workers use, levels 1/4/6), pigz, rapidgzip (parallel decompression of
  ordinary gzip), and bgzip (BGZF compress and decompress).
- `scripts/io_variants.sh` runs **the same fastp binary on the same reads** with codec
  stages switched on and off:

  | variant | input | output | removes |
  |---|---|---|---|
  | `gz_gz` | sequencer `.gz` | `.gz -z 4` | nothing (the normal run) |
  | `gz_gz_z1` | `.gz` | `.gz -z 1` | some compression effort |
  | `gz_plain` | `.gz` | `.fq` | output compression |
  | `gz_none` | `.gz` | none | compression + write (QC/report only) |
  | `plain_gz` | `.fq` | `.gz` | input decompression |
  | `plain_plain` | `.fq` | `.fq` | both codecs |
  | `plain_none` | `.fq` | none | codecs + write: **the per-read compute floor** |
  | `bgzf_gz` / `bgzf_plain` | BGZF `.gz` | `.gz` / `.fq` | single-thread inflate (uses the parallel BGZF reader) |

  Each run also records per-thread CPU (`scripts/threadcpu.py`, via `bench_full.py` with
  `FASTP_BENCH_THREADS_JSON`), so a pinned reader thread is visible directly. The one-off
  cost of making the `.fq` and BGZF inputs goes to `<work_dir>/prep.tsv`, since any
  approach that needs converted input has to pay it.

- `scripts/decompose.py` turns both into a per-cell breakdown: wall and CPU for each
  variant, the difference each stage makes, the **reader ceiling** (largest mate's
  uncompressed bytes ÷ single-thread igzip MB/s), and the busiest threads.

Reading the results:

- **CPU-second differences add up**; they are the cost side (CPU-hours per sample).
  **Wall differences don't**: stages overlap across threads, so removing one saves
  wall time only if it was on the critical path.
- If `gz_gz` processing time ≈ the reader ceiling, and one thread sits near 100%
  busy while workers idle, the run is decompression-bound. Faster per-read code won't help;
  parallel decompression (BGZF input, rapidgzip, GPU inflate) would.
- `plain_none` CPU ÷ `gz_gz` CPU is the share of CPU a GPU port of the per-read work could
  remove at most, before paying for moving data to the GPU and back
  (see the reformulation cost model, stacked on this PR).
- Outputs must not depend on I/O mode: `decompose.py` flags any variant whose decompressed
  output digest differs from the others.

## Results

_Pending: n2d-highmem-48 runs on the full-size datasets from [full-size.md](full-size.md)
(`rna_nova`, `wgbs`, `atac_hiseq` PE and `rna_se` SE), at `-w 16` and `-w 48`._

## Running it

```bash
# data/ from scripts/fetch_full.sh; work/ needs ~4x the compressed size free (plain + BGZF copies)
bash scripts/codec_baselines.sh data work results/codec.tsv "rna_nova wgbs" 1,4,16,48
bash scripts/io_variants.sh bin/fastp-master data work results/io.tsv "rna_nova:PE wgbs:PE" 16,48 2
python3 scripts/decompose.py results/io.tsv results/codec.tsv --prep work/prep.tsv --md results/codec-io.md
```

Needs `isal` (igzip), `libdeflate-tools`, `pigz`, `tabix` (bgzip), `time`, and
`pip install rapidgzip`. Missing codec tools are skipped.
