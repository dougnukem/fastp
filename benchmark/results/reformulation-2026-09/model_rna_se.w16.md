# Reformulation projection

Sample: 42,623,602 reads per mate x 1 mate(s); CPU box 48 vCPUs, fastp -w 16.
Measured per read (trace): decompress 184 ns, parse 751, process 5387, compress 1715, write 36. Transforms (soa_pack): index 31, pack 23, emit 35, CPU kernel 543.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 344.1 | 0.0 | 0.0 | 39.9 | 1.00x | - | reader 40s vs workers 19s |
| D1 BGZF input | 344.1 | 151.2 | 0.0 | 32.3 | 1.23x | - | pool 29 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 378.6 | 0.0 | 0.0 | 33.5 | 1.19x | - | CPU/byte x5.39 vs ISA-L (from codec baselines) |
| D3 -z 1 | 305.4 | 0.0 | 0.0 | 39.9 | 1.00x | - | compress x2.1 faster, output larger |
| D4 uncompressed stream to aligner | 271.0 | -7.8 | 0.0 | 39.9 | 1.00x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 314.4 | -29.8 | 0.0 | 19.0 | 2.10x | - | reader 10s vs workers 19s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 97x (measured kernel) | 86.2 | -29.8 | 2.9 | 10.1 | 3.94x | - | PCIe 13 ns/read; QC share of process 99% |
| B GPU-resident, QC 97x (measured kernel) | 3.7 | 0.0 | 14.5 | 14.2 | 2.81x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.75 |
| C fused into GPU aligner, QC 97x (measured kernel) | 0.0 | -7.8 | 2.4 | 2.4 | 16.91x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 86.2 | -29.8 | 76.6 | 76.6 | 0.52x | - | PCIe 13 ns/read; QC share of process 99% |
| B GPU-resident, QC 3x (assumed) | 3.7 | 0.0 | 88.6 | 88.3 | 0.45x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.75 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -7.8 | 76.5 | 76.5 | 0.52x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 86.2 | -29.8 | 23.4 | 23.4 | 1.71x | - | PCIe 13 ns/read; QC share of process 99% |
| B GPU-resident, QC 10x (assumed) | 3.7 | 0.0 | 35.1 | 34.8 | 1.15x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.75 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -7.8 | 22.9 | 22.9 | 1.74x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
