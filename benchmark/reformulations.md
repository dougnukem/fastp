# Reformulating fastp for GPUs (and the alternatives)

Can fastp's problem be reshaped so a GPU speeds it up? And does that still win once you count
the cost of converting data into and out of the GPU's format? This page covers what exists
already, the ways to reformulate, what each costs as measured by the tools in this stack, and
where each one is actually useful.

Measurements come from:
[codec-io.md](codec-io.md) (stages switched off), [trace.md](trace.md) (per-read cost of each
stage inside a run), `tools/soa_pack.cpp` (CPU cost of the transforms), `tools/gpu_bench.py`
(GPU side), and `scripts/reformulation_model.py`, which combines them.

## What makes work a GPU candidate

A GPU wins when all of these hold. Missing one usually cancels the gain.

1. Tens of thousands of independent work items, with little shared state.
2. Uniform control flow. Threads run in 32-wide warps, and divergent branches or early exits
   serialise.
3. Many operations per byte moved. PCIe (~25 GB/s on Gen4 x16) is slower than CPU memory,
   so a few cheap operations per byte lose to the copy.
4. Regular memory access: fixed-size records, not pointer chasing.
5. Batches large enough (≥10⁶ items) to amortise launch and transfer latency.
6. The accelerated part dominates the run (Amdahl).
7. It's cheaper per sample, not only faster. A GPU VM has to replace more CPU-hours than it costs.

fastp's per-read QC meets 1, 4 and 5, meets 2 partly (adapter search exits early and reads
vary in length), and fails 3: it does roughly O(read length) cheap operations per byte. It meets
6 only if codecs and parsing aren't the critical path. The measurements below test that.

## What already exists (literature and GitHub, checked 2026-09-28)

| Tool / work | Kind | What it reports | Relevance |
|---|---|---|---|
| **No GPU FASTQ trimmer/QC tool found** | – | Searches for GPU ports of fastp, cutadapt, Trimmomatic and AfterQC, plus CUDA adapter trimming, found no maintained tool. | Any GPU fastp would be new work. |
| [NVIDIA Parabricks](https://docs.nvidia.com/clara/parabricks/) `fq2bam` | GPU pipeline | BWA-MEM alignment, sorting, duplicate marking and BQSR on GPU. No trimming or QC stage; workflows such as nf-core/sarek run fastp on CPU before it. | Reformulation C (fuse QC into the aligner) has no hook to use today. |
| [nvCOMP](https://docs.nvidia.com/cuda/nvcomp/release_notes.html) ≥ 5.2 | GPU codec | Batched Deflate/Gzip decompression since 2.3/2.5. **5.2.0 added `NVCOMP_GZIP_DECOMPRESS_ALGORITHM_LOOKAHEAD`, "significantly better decompression throughput when decompressing single large buffers", and the [`nvlzcat`](https://docs.nvidia.com/cuda/nvcomp/nvlzcat.html) CLI for single gzip streams.** 5.3.0 added GZIP compression. | Ordinary single-member `.fastq.gz` (what sequencers write) can be inflated on a GPU without BGZF. Measured below. |
| [nvCOMP Decompression Engine](https://docs.nvidia.com/cuda/nvcomp/decompression_engine_faq.html) | GPU hardware | B200/B300/GB200/GB300 only: Snappy, Deflate/Gzip and LZ4 decompression "up to 600 GB/s", chunks ≤ 4 MiB. | Not on L4/A100/H100. Chunked input only. |
| [rapidgzip](https://github.com/mxmlnkn/rapidgzip) (Knespel & Brunst) | CPU parallel inflate | Parallel decompression of arbitrary gzip. Ryzen 3900X, 12 threads: 4.46 GB/s (base64 data, with index). 2× EPYC 7702, 128 cores: "up to 24 GB/s with an index and 12 GB/s without" (Silesia). Header-only C++ library; index export/import. | Removes fastp's one-inflate-thread-per-mate ceiling on CPU, with no format change. |
| [pugz](https://github.com/Piezoid/pugz) | CPU parallel inflate | Parallel gzip decompression, restricted to text (byte values 9–126), which FASTQ satisfies. | Same idea as rapidgzip, narrower scope. |
| [RabbitQCPlus 2.0](https://github.com/RabbitBio/RabbitQCPlus) (Methods 2023) | CPU QC tool | "1.1 to 5.4 times faster" basic QC; "at least 4 times faster" on gzip input "by integrating a parallel (de)compression engine". Baseline was **fastp 0.23.2**. | The gap is from parallel codecs, and fastp 1.x has since added parallel output compression and a BGZF reader. The remaining difference is the gzip *input* path. |
| [Helicase](https://github.com/imartayan/helicase) (bioRxiv 2026) | CPU SIMD parser | Vectorised FASTQ record scanning and 2-bit packing; faster than the parsers it benchmarks against (absolute numbers not extracted). | Parsing is also a CPU SIMD problem, not a GPU one. |
| [Gerbil](https://github.com/uni-halle/gerbil) | GPU k-mer counting | Up to ~4× vs other k-mer counters on large genomes, k ≥ 32. | fastp's k-mer and duplication stats are sampled and small; not a bottleneck. |

The survey points the same way as the source: the published wins over fastp come from
**parallel decompression**, not from faster per-read work.

## How fastp spends threads today (1.3.x)

Details are in [codec-io.md](codec-io.md). In short:
- Ordinary `.gz` input is inflated **and** parsed by one reader thread per mate.
- Output compression is already parallel (libdeflate in each worker, then ordered `pwrite`).
- BGZF input gets a decompression pool of `max(1, (nproc − (-w + 4)) / inputs)` threads,
  which drops to 1 at high `-w`.

## The reformulations

For each one: what changes, what data transformation it needs, and what that costs.
Measured numbers are in the next section.

### D1. BGZF input (CPU, format change)
fastp already reads BGZF in parallel. **Transform:** if the sequencer wrote ordinary gzip, it
has to be recompressed once (inflate + BGZF deflate, `prep.tsv`). That costs more CPU than
fastp's own inflate, so it only pays if the file is read several times or the demultiplexer
can write BGZF directly. **Also:** the pool is sized from leftover cores, so at high `-w` it
gets 1 thread and the gain disappears unless the formula changes.

### D2. Parallel inflate of ordinary gzip in the reader (CPU, no format change)
Swap ISA-L's single stream in `FastqReader` for rapidgzip-style parallel decompression.
**Transform:** none. **Cost:** extra CPU per byte for speculative decoding and window
resolution (measured as rapidgzip's CPU/byte vs igzip's). This is the direct fix for a
reader-bound run and needs no GPU.

### D3. Cheaper output compression (CPU)
`-z 1` or a faster codec level. **Transform:** none. **Cost:** larger output files, which
means more storage and more bytes for the next tool to inflate.

### D4. Don't compress the intermediate at all (CPU, pipeline change)
When the next step reads fastp's output once (an aligner), stream it uncompressed
(`--stdout` into the aligner, or a named pipe). This removes fastp's compression **and** the
aligner's decompression of trimmed reads. The `gz_plain` variant gives the first half;
the aligner's inflate cost is the second.

### D5. A cheaper parser (CPU)
The reader indexes records and packs them into a flat batch instead of allocating a `Read`
object (4 strings) per record. **Transform:** none; this *is* the parse. **Cost:**
fastp's per-read code would have to work on views into the batch. `soa_pack`'s index + pack
(40–70 ns/read) is the lower bound, against fastp's measured 670–1100 ns/read. This is also
option A's parser, so A's GPU contribution is A vs D5, not A vs base.

### D6. Shard across machines (CPU)
FASTQ splits by record count, so K VMs run K× faster for the same CPU-hours.
**Transform:** splitting cost, or none if the demultiplexer writes per-lane or per-tile files.
This fixes turnaround, not cost.

### D7. Right-size `-w`
On a 24-core / 48-vCPU box, `-w 16` beat `-w 48` on 3 of 4 datasets, and `-w 48` spent
25–45% more CPU. **Transform:** none. It's a default and documentation change.

### A. Offload only the per-read QC to a GPU
The CPU keeps inflate, parses into a fixed-stride SoA batch instead of `Read` objects, and
sends the batch to the GPU. The GPU returns a 4-byte decision per read (trim end, pass). The
CPU then serialises the kept reads and compresses them.
**Transforms:** index + pack on the CPU (`soa_pack`: index, pack); PCIe for the batch
(`soa_fixed` bytes/read); serialise from decisions (emit).
**Limit:** the reader still inflates on one thread and workers still compress, so A can't
go faster than those stages. It only helps a worker-bound run where QC, not compression,
fills the workers. 2-bit packing isn't worth it: it costs 4–5× the plain pack and saves
~30% of bytes, because quality bytes dominate.

### B. GPU-resident fastp
Compressed bytes go to the GPU. The GPU inflates (single-stream lookahead for ordinary gzip,
or batched for BGZF), parses, runs QC and compresses; compressed bytes come back.
**Transforms:** none on the CPU. PCIe carries compressed bytes only. **Costs and risks:**
- GPU gzip compression ratio vs libdeflate `-z 4` (measured). A worse ratio means more
  storage and more downstream I/O.
- No GPU FASTQ parser exists, so parse cost is modelled, not measured.
- fastp's report features (duplication, overrepresentation, k-mer, per-position stats) all
  need GPU versions.
- The output must stay byte-compatible in what it keeps and trims.

### C. Fuse QC into a GPU aligner
If alignment already runs on a GPU (Parabricks `fq2bam`), QC becomes a kernel on reads that
are already on the device. fastp's whole CPU cost disappears, and so does writing then
re-reading the trimmed `.fastq.gz`.
**Blocker:** it needs a pre-alignment hook in the aligner, which Parabricks doesn't expose.
Viable in an open GPU aligner, or if NVIDIA added trimming.

## Measured results

CPU box: n2d-highmem-48 (EPYC Milan, 24 cores / 48 vCPUs). GPU box: g2-standard-8 with one
NVIDIA L4 (PCIe), nvCOMP 5.3.0. Same four complete public datasets as
[codec-io.md](codec-io.md#results). Everything is in
[`results/reformulation-2026-09/`](results/reformulation-2026-09/).

### What fastp spends, per read (trace build, gz→gz, `-w 16`)

| dataset | inflate | parse | per-read work | compress | bound by |
|---|---|---|---|---|---|
| rna_nova (PE 150) | 300 ns | 783 ns | 9,380 ns | 2,714 ns | workers |
| wgbs (PE 90) | 286 | 799 | 5,699 | 2,739 | reader |
| atac_hiseq (PE 50) | 180 | 672 | 3,935 | 1,570 | reader |
| rna_se (SE 75) | 184 | 751 | 5,387 | 1,715 | reader |

Per-read work is 60–70% of traced CPU. Within the workers, 36% is adapter search by
sequence, and 33 points of that are one function, which also has a bug (see [trace.md](trace.md#trimbysequences-one-gap-search-doesnt-advance-through-the-read)),
~20% compression, 11% stats and 4% duplication.

### Transform costs (CPU, `soa_pack`, per read)

| dataset | index | pack (SoA) | pack (2-bit) | emit FASTQ from decisions | SoA bytes | text bytes |
|---|---|---|---|---|---|---|
| rna_nova | 33 ns | 37 | 193 | 46 | 302 | 336 |
| wgbs | 33 | 26 | 118 | 39 | 182 | 245 |
| atac_hiseq | 29 | 15 | 65 | 30 | 102 | 169 |
| rna_se | 31 | 23 | 109 | 35 | 152 | 218 |

Getting reads into and out of a GPU-friendly batch costs **~80–120 ns per read**, about a
tenth of fastp's own parse. 2-bit packing costs 4–5× the plain pack but saves only ~30% of
bytes, because the quality bytes dominate. It isn't worth it for PCIe.

### The GPU side (L4)

| step | measured | vs CPU |
|---|---|---|
| PCIe host→device, pinned | 12.3 GB/s | – |
| analogue QC kernel (1,048,576 real reads, 150 bp) | **5.6 ns/read**, 0 decision mismatches vs CPU | 1,163 ns/read on one EPYC thread (209×) |
| copying that batch to the GPU | **24.5 ns/read** | 4× the kernel: transfer-bound |
| inflate ordinary single-member `.gz` (`nvlzcat`, lookahead) | 1.26 GB/s end to end | ISA-L 1 thread: 0.81 GB/s; rapidgzip 16 threads: 3.4 GB/s |
| inflate, nvCOMP Python default (no lookahead), 100 MB member | 0.031 GB/s | 40× slower than lookahead |
| inflate BGZF blocks, batched (device-resident) | 7.3 GB/s | bgzip 16 threads: 9.0 GB/s |
| gzip compress, `nvlzcat -a 0/1/2` | 3.4 / 3.1 / 2.1 GB/s, ratio 2.76 / 3.16 / **4.61** | libdeflate `-z 4` 1 thread: 0.125 GB/s, ratio 4.93 |
| gzip compress, `nvlzcat -a 4/5` | 0.12 GB/s, ratio 4.88 / 5.12 | ≈ 1 libdeflate thread |
| Deflate compress via nvCOMP Python API | 2–42 MB/s | an API-path problem (1000× slower than `nvlzcat`); excluded |

`nvlzcat -a 1` output round-trips through ISA-L as standard gzip.

### Projected wall time per reformulation (`reformulation_model.py`, `-w 16`)

Wall is the slowest overlapped stage. "Kernel ×" applies the analogue kernel's measured
CPU/GPU ratio to all of fastp's per-read work. The "@10×" and "@3×" columns assume fastp's
real per-read work (which includes the branchy gap search, stats and duplication hashing)
speeds up only 10× or 3× on the GPU. Full tables, including `-w 48` and CPU/GPU seconds, are in
`model_<dataset>.w{16,48}.md`.

| dataset | base | D1 BGZF | D2 par. gzip | D3 `-z 1` | D4 stream | D5 parser | A (kernel ×) | A @10× | A @3× | B (kernel ×) | C (kernel ×) | C @10× |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rna_nova | 47 s | 1.00× | 1.00× | 1.13× | 1.29× | 1.00× | 4.13× (209×) | 0.80× | 0.24× | 1.61× | 17× | 0.82× |
| wgbs | 31 s | 1.02× | 1.02× | 1.00× | 1.00× | 1.02× | 3.08× (121×) | 0.93× | 0.29× | 0.24×¹ | 12× | 0.95× |
| atac_hiseq | 164 s | 1.23× | 1.16× | 1.00× | 1.00× | 1.23× | 3.81× (67×) | 1.07× | 0.32× | 1.55× | 7.3× | 1.08× |
| rna_se | 40 s | 1.23× | 1.19× | 1.00× | 1.00× | **2.10×** | 3.94× (97×) | 1.71× | 0.52× | 2.81× | 17× | 1.74× |

¹ wgbs compresses to 5.34 with libdeflate `-z 4`. No fast GPU gzip level comes within 90%
of that (`-a 2` reaches 4.61), so B falls back to the slow high-ratio level.

CPU seconds per sample (base → A at kernel speed): rna_nova 826 → 202, wgbs 543 → 180,
atac_hiseq 2470 → 721, rna_se 344 → 86. That's a **~70–75% cut in CPU**, bought with one
GPU's 3–26 s. At only 10× on the real work, the GPU needs 23–154 s, and one L4 is then
about as fast as 16 EPYC threads.

## Where each is useful

**Do first, on CPU (no GPU, no format change):**

1. **Fix and speed up `trimBySequence`'s gap search.** It's the single largest CPU item
   (a third of worker time). It's also a correctness bug: the one-gap search never advances
   through the read. The fix makes it +28–42% more expensive, so it has to ship with a faster
   algorithm.
2. **Cheaper parsing (D5).** The reader's parse is the critical path in 6 of 8 gz cells. A
   flat-batch parser projects 1.2–2.1× on reader-bound data by itself.
3. **Right-size threads (D7).** Keep `-w` at or below the physical core count minus the
   readers. Stop idle workers polling on 1 ms timeouts: `-w 48` is slower and costs 25–45%
   more CPU than `-w 16` here.
4. **Stream uncompressed output to the aligner (D4)** when the next step reads it once. That
   removes 18–25% of fastp's CPU plus the aligner's inflate. `-z 1` (D3) is a smaller version of
   the same trade: −12% CPU, slightly larger files.

**Not worth it:** BGZF input (D1). The conversion costs ~5.7 µs of CPU per read, more than
fastp spends reading it, and it doesn't lift the parse bottleneck. It's only worth it if the
demultiplexer can write BGZF directly. The parallel gzip reader (D2) is correct but only helps
reader-bound runs, and it spends ~3.7× the CPU per byte.

**GPU, only in these shapes:**

- **A (offload per-read QC)** pays off only for cost (CPU-hours), and only if fastp's *real*
  per-read work, not the analogue kernel, runs at ≥ ~10–15× one CPU thread on the GPU. The
  analogue measured 67–209×, but covers about 1/8 of fastp's per-read work and has none of the
  gap search's branchiness. Transfers already cost 4× the analogue kernel. The deciding
  experiment is to port `trimBySequence` (with the fix) and `statRead` to the GPU and measure
  them.
- **B (GPU-resident)** is limited by single-stream gzip inflate (1.26 GB/s on L4, below 16 CPU
  threads of rapidgzip) and by GPU gzip's ratio. At fastp's `-z 4` ratio, GPU compression is no
  faster than one CPU core. B makes sense only with BGZF input and a relaxed output ratio.
  Neither is fastp's current contract.
- **C (fused into a GPU aligner)** is the only shape where both transfers disappear. It's the
  one real GPU opportunity, but it needs a pre-alignment hook that Parabricks doesn't expose.
  Worth raising with NVIDIA or an open GPU-aligner project.

**Bottom line.** fastp isn't GPU-shaped as it stands. Its time goes to a serial parser, a
branchy adapter search, and codecs whose GPU versions are slower than a handful of CPU cores
at the same ratio. The largest measured wins are CPU changes (1–3 above), and one of them
fixes a correctness bug. A GPU becomes interesting once fastp's per-read work is a flat batch
kernel (after D5). It's most interesting inside a GPU pipeline that already holds the reads.

## Reproducing

```bash
# CPU box (bin/ has fastp, fastp-trace, soa_pack)
bash scripts/fetch_full.sh data "rna_nova:SRR10007843:PE wgbs:ERR10308506:PE atac_hiseq:SRR891268:PE rna_se:ERR10669429:SE"
bash scripts/run_reformulation_suite.sh bin data work results "rna_nova:PE wgbs:PE atac_hiseq:PE rna_se:SE" 16,48 2
# ENA serves ~1 MB/s per connection: fetching with aria2c -x 16 is much faster than fetch_full.sh
# GPU box (pip: cupy-cuda12x nvidia-nvcomp-cu12; nvlzcat from the nvCOMP >= 5.2 tarball)
./soa_pack data/rna_nova_R1.fastq 1048576 --dump soa_rna_nova
python3 tools/gpu_bench.py --soa soa_rna_nova --bgzf rna_nova_R1.bgzf.fastq.gz --gz rna_nova_R1.fastq.gz --plain rna_nova_R1.fastq --json gpu.json
# model (commands printed by the suite)
python3 scripts/reformulation_model.py --trace results/trace/rna_nova.gz.w48.json --soa results/soa_rna_nova.json --gpu gpu.json --dataset rna_nova ...
```
