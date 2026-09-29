# Reformulation projection

Sample: 192,904,649 reads per mate x 2 mate(s); CPU box 48 vCPUs, fastp -w 48.
Measured per read (trace): decompress 194 ns, parse 967, process 4828, compress 1817, write 103. Transforms (soa_pack): index 29, pack 15, emit 30, CPU kernel 374.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 3051.5 | 0.0 | 0.0 | 223.9 | 1.00x | - | reader 224s vs workers 54s |
| D1 BGZF input | 3051.5 | 630.7 | 0.0 | 223.9 | 1.00x | - | pool 1 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 3335.6 | 0.0 | 0.0 | 366.0 | 0.61x | - | CPU/byte x4.80 vs ISA-L (from codec baselines) |
| D3 -z 1 | 2652.1 | 0.0 | 0.0 | 223.9 | 1.00x | - | compress x2.3 faster, output larger |
| D4 uncompressed stream to aligner | 2350.5 | -74.7 | 0.0 | 223.9 | 1.00x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 2695.2 | -356.3 | 0.0 | 54.2 | 4.13x | - | reader 46s vs workers 54s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 67x (measured kernel) | 844.2 | -356.3 | 30.9 | 45.8 | 4.89x | - | PCIe 9 ns/read; QC share of process 99% |
| B GPU-resident, QC 67x (measured kernel) | 59.2 | 0.0 | 113.3 | 110.9 | 2.02x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 3.64 |
| C fused into GPU aligner, QC 67x (measured kernel) | 0.0 | -74.7 | 27.8 | 27.8 | 8.07x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 844.2 | -356.3 | 620.3 | 620.3 | 0.36x | - | PCIe 9 ns/read; QC share of process 99% |
| B GPU-resident, QC 3x (assumed) | 59.2 | 0.0 | 706.3 | 703.8 | 0.32x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 3.64 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -74.7 | 620.7 | 620.7 | 0.36x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 844.2 | -356.3 | 188.4 | 188.4 | 1.19x | - | PCIe 9 ns/read; QC share of process 99% |
| B GPU-resident, QC 10x (assumed) | 59.2 | 0.0 | 271.8 | 269.3 | 0.83x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 3.64 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -74.7 | 186.2 | 186.2 | 1.20x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
