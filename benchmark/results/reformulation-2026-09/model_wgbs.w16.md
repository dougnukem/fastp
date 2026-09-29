# Reformulation projection

Sample: 28,380,374 reads per mate x 2 mate(s); CPU box 48 vCPUs, fastp -w 16.
Measured per read (trace): decompress 286 ns, parse 799, process 5699, compress 2739, write 42. Transforms (soa_pack): index 33, pack 26, emit 39, CPU kernel 677.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 542.9 | 0.0 | 0.0 | 30.8 | 1.00x | - | reader 31s vs workers 30s |
| D1 BGZF input | 542.9 | 103.6 | 0.0 | 30.1 | 1.02x | - | pool 14 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 621.7 | 0.0 | 0.0 | 30.1 | 1.02x | - | CPU/byte x5.85 vs ISA-L (from codec baselines) |
| D3 -z 1 | 467.5 | 0.0 | 0.0 | 30.8 | 1.00x | - | compress x1.9 faster, output larger |
| D4 uncompressed stream to aligner | 387.5 | -16.3 | 0.0 | 30.8 | 1.00x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 500.9 | -42.0 | 0.0 | 30.1 | 1.02x | - | reader 10s vs workers 30s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 121x (measured kernel) | 179.6 | -42.0 | 3.5 | 10.0 | 3.08x | - | PCIe 15 ns/read; QC share of process 99% |
| B GPU-resident, QC 121x (measured kernel) | 5.2 | 0.0 | 126.3 | 125.8 | 0.24x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a5, ratio 5.12 vs libdeflate 5.17 |
| C fused into GPU aligner, QC 121x (measured kernel) | 0.0 | -16.3 | 2.7 | 2.7 | 11.56x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 179.6 | -42.0 | 107.9 | 107.9 | 0.29x | - | PCIe 15 ns/read; QC share of process 99% |
| B GPU-resident, QC 3x (assumed) | 5.2 | 0.0 | 231.3 | 230.8 | 0.13x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a5, ratio 5.12 vs libdeflate 5.17 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -16.3 | 107.7 | 107.7 | 0.29x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 179.6 | -42.0 | 33.0 | 33.0 | 0.93x | - | PCIe 15 ns/read; QC share of process 99% |
| B GPU-resident, QC 10x (assumed) | 5.2 | 0.0 | 155.9 | 155.4 | 0.20x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a5, ratio 5.12 vs libdeflate 5.17 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -16.3 | 32.3 | 32.3 | 0.95x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
