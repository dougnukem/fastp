# Reformulation projection

Sample: 192,904,649 reads per mate x 2 mate(s); CPU box 48 vCPUs, fastp -w 16.
Measured per read (trace): decompress 180 ns, parse 672, process 3935, compress 1570, write 45. Transforms (soa_pack): index 29, pack 15, emit 30, CPU kernel 374.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 2469.9 | 0.0 | 0.0 | 164.3 | 1.00x | - | reader 164s vs workers 134s |
| D1 BGZF input | 2469.9 | 630.7 | 0.0 | 133.8 | 1.23x | - | pool 14 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 2733.3 | 0.0 | 0.0 | 141.5 | 1.16x | - | CPU/byte x4.80 vs ISA-L (from codec baselines) |
| D3 -z 1 | 2124.8 | 0.0 | 0.0 | 164.3 | 1.00x | - | compress x2.3 faster, output larger |
| D4 uncompressed stream to aligner | 1864.1 | -69.2 | 0.0 | 164.3 | 1.00x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 2227.5 | -242.4 | 0.0 | 133.8 | 1.23x | - | reader 43s vs workers 134s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 67x (measured kernel) | 720.8 | -242.4 | 25.8 | 43.1 | 3.81x | - | PCIe 9 ns/read; QC share of process 99% |
| B GPU-resident, QC 67x (measured kernel) | 36.5 | 0.0 | 108.2 | 105.7 | 1.55x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 3.64 |
| C fused into GPU aligner, QC 67x (measured kernel) | 0.0 | -69.2 | 22.6 | 22.6 | 7.26x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 720.8 | -242.4 | 505.5 | 505.5 | 0.32x | - | PCIe 9 ns/read; QC share of process 99% |
| B GPU-resident, QC 3x (assumed) | 36.5 | 0.0 | 591.5 | 589.0 | 0.28x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 3.64 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -69.2 | 505.9 | 505.9 | 0.32x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 720.8 | -242.4 | 154.0 | 154.0 | 1.07x | - | PCIe 9 ns/read; QC share of process 99% |
| B GPU-resident, QC 10x (assumed) | 36.5 | 0.0 | 237.3 | 234.9 | 0.70x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 3.64 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -69.2 | 151.8 | 151.8 | 1.08x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
