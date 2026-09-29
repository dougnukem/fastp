# Reformulation projection

Sample: 42,623,602 reads per mate x 1 mate(s); CPU box 48 vCPUs, fastp -w 48.
Measured per read (trace): decompress 194 ns, parse 893, process 6369, compress 1911, write 44. Transforms (soa_pack): index 31, pack 23, emit 35, CPU kernel 543.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 401.1 | 0.0 | 0.0 | 46.3 | 1.00x | - | reader 46s vs workers 7s |
| D1 BGZF input | 401.1 | 151.2 | 0.0 | 46.3 | 1.00x | - | pool 1 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 437.4 | 0.0 | 0.0 | 82.6 | 0.56x | - | CPU/byte x5.39 vs ISA-L (from codec baselines) |
| D3 -z 1 | 358.0 | 0.0 | 0.0 | 46.3 | 1.00x | - | compress x2.1 faster, output larger |
| D4 uncompressed stream to aligner | 319.7 | -8.2 | 0.0 | 46.3 | 1.00x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 365.3 | -35.8 | 0.0 | 10.5 | 4.40x | - | reader 11s vs workers 7s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 97x (measured kernel) | 95.3 | -35.8 | 3.3 | 10.5 | 4.40x | - | PCIe 13 ns/read; QC share of process 99% |
| B GPU-resident, QC 97x (measured kernel) | 4.0 | 0.0 | 14.9 | 14.6 | 3.17x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.75 |
| C fused into GPU aligner, QC 97x (measured kernel) | 0.0 | -8.2 | 2.8 | 2.8 | 16.62x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 95.3 | -35.8 | 90.5 | 90.5 | 0.51x | - | PCIe 13 ns/read; QC share of process 99% |
| B GPU-resident, QC 3x (assumed) | 4.0 | 0.0 | 102.6 | 102.2 | 0.45x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.75 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -8.2 | 90.4 | 90.4 | 0.51x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 95.3 | -35.8 | 27.5 | 27.5 | 1.68x | - | PCIe 13 ns/read; QC share of process 99% |
| B GPU-resident, QC 10x (assumed) | 4.0 | 0.0 | 39.2 | 38.9 | 1.19x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.75 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -8.2 | 27.1 | 27.1 | 1.71x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
