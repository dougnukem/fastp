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

n2d-highmem-48 (AMD EPYC Milan, 48 vCPUs = 24 cores × 2 SMT threads, 384 GB), 2 local
NVMe SSDs in RAID 0, inputs in the page cache. The binary is this stack plus #723's
backpressure fix (upstream 1.3.7 deadlocks at `-w 48`, #721). Complete public runs:
`rna_nova` (SRR10007843, NovaSeq PE 150, 31M pairs), `wgbs` (ERR10308506, NextSeq PE,
28M pairs), `atac_hiseq` (SRR891268, HiSeq PE 50, 193M pairs) and `rna_se` (ERR10669429,
HiSeq SE 75, 43M reads). Medians of 2 reps. Raw data and the full `decompose.py` report are in
[`results/codec-io-2026-09/`](results/codec-io-2026-09/).

| dataset | -w | wall gz→gz | wall, no codecs (`plain_none`) | wall, plain input (`plain_gz`) | wall, BGZF input | CPU gz→gz | CPU compress share | CPU decompress share | CPU per-read floor share |
|---|---|---|---|---|---|---|---|---|---|
| atac_hiseq | 16 | 200 s | 185 s | 168 s | 195 s | 2598 | 19% | 3% | 76% |
| atac_hiseq | 48 | 270 s | 236 s | 234 s | 270 s | 3473 | 19% | 4% | 75% |
| rna_nova | 16 | 62 s | 46 s | 58 s | 68 s | 862 | 18% | 4% | 76% |
| rna_nova | 48 | 59 s | 49 s | 50 s | 62 s | 1240 | 22% | 1% | 76% |
| rna_se | 16 | 43 s | 35 s | 35 s | 45 s | 369 | 18% | 5% | 76% |
| rna_se | 48 | 54 s | 46 s | 46 s | 57 s | 457 | 17% | 3% | 80% |
| wgbs | 16 | 71 s | 58 s | 61 s | 70 s | 598 | 25% | 5% | 70% |
| wgbs | 48 | 78 s | 69 s | 69 s | 83 s | 763 | 25% | -3% | 74% |

Output digests are identical across every variant and thread count for each dataset
(72 cells, one digest per dataset). I/O mode changes timing only.

What it shows:

1. **Per-read work, not codecs, is ~75% of CPU** (`plain_none` ÷ `gz_gz`) on every dataset.
   Output compression is 17–25%. Input decompression is 1–5%.
2. **Removing both codecs saves only 13–26% of wall time**, so no codec change alone (GPU or
   CPU) can speed fastp up more than that.
3. **`-w 48` is slower than `-w 16`** on 3 of 4 datasets (atac 200 → 270 s) and costs 25–45%
   more CPU. 48 vCPUs are 24 physical cores. At `-w 48` the serial reader threads share
   cores with workers, and the per-read cost of every stage rises (see [trace.md](trace.md)).
   Idle workers also poll their queues on 1 ms timed waits.
4. **Plain input helps only when the reader is the bottleneck** (atac −32 s, rna_nova at
   `-w 48` −9 s). That is the reader's single-threaded inflate coming off the critical path.
5. **BGZF input doesn't help and costs CPU** (+0–15% CPU, wall equal or worse). The parallel
   BGZF reader removes inflate from the reader thread, but parsing stays there and is the larger part
   ([trace.md](trace.md)). The one-off conversion to BGZF (`prep.tsv`) costs 12 CPU-s
   (inflate) + 165 CPU-s (bgzip `-l 4`) per `rna_nova` mate, about 5.7 µs of CPU per read. That's
   more than fastp spends decompressing and parsing the read.

Standalone codecs (`codec.tsv`, `codec_parallel_uncapped.tsv`), per 10.4 GB `rna_nova` mate:

| codec | threads | MB/s (uncompressed) | CPU-s | ratio |
|---|---|---|---|---|
| ISA-L inflate (fastp's reader) | 1 | 808 | 12 | – |
| rapidgzip, ordinary gzip | 16 / 48 | 3,433 / 5,831 | 46 / 69 | – |
| bgzip inflate, BGZF | 16 | 8,998 | 16 | – |
| libdeflate `-1` / `-4` / `-6` (fastp's writer, `-z`) | 1 | 257 / 125 / 64 | – | 4.68 / 4.93 / 5.15 |
| ISA-L `-1` | 1 | 460 | – | 4.51 |

Parallel decompressors in `codec.tsv` were capped at ~2.5 GB/s by a `wc -c` pipe. That's fixed in
`codec_baselines.sh`, and the uncapped reruns are in `codec_parallel_uncapped.tsv`. rapidgzip
spends ~3.7× ISA-L's CPU per byte (index-free speculative decoding). BGZF decompression
is about as efficient as ISA-L, but only once the input is BGZF.

## Running it

```bash
# data/ from scripts/fetch_full.sh; work/ needs ~4x the compressed size free (plain + BGZF copies)
bash scripts/codec_baselines.sh data work results/codec.tsv "rna_nova wgbs" 1,4,16,48
bash scripts/io_variants.sh bin/fastp-master data work results/io.tsv "rna_nova:PE wgbs:PE" 16,48 2
python3 scripts/decompose.py results/io.tsv results/codec.tsv --prep work/prep.tsv --md results/codec-io.md
```

Needs `isal` (igzip), `libdeflate-tools`, `pigz`, `tabix` (bgzip), `time`, and
`pip install rapidgzip`. Missing codec tools are skipped.
