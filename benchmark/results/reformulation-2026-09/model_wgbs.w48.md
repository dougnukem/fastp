# Reformulation projection

Sample: 28,380,374 reads per mate x 2 mate(s); CPU box 48 vCPUs, fastp -w 48.
Measured per read (trace): decompress 315 ns, parse 1001, process 7105, compress 3190, write 62. Transforms (soa_pack): index 33, pack 26, emit 39, CPU kernel 677.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 662.6 | 0.0 | 0.0 | 37.4 | 1.00x | - | reader 37s vs workers 12s |
| D1 BGZF input | 662.6 | 103.6 | 0.0 | 37.4 | 1.00x | - | pool 1 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 749.4 | 0.0 | 0.0 | 80.8 | 0.46x | - | CPU/byte x5.85 vs ISA-L (from codec baselines) |
| D3 -z 1 | 574.8 | 0.0 | 0.0 | 37.4 | 1.00x | - | compress x1.9 faster, output larger |
| D4 uncompressed stream to aligner | 481.5 | -17.9 | 0.0 | 37.4 | 1.00x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 609.1 | -53.5 | 0.0 | 12.2 | 3.05x | - | reader 11s vs workers 12s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 121x (measured kernel) | 208.0 | -53.5 | 4.2 | 10.6 | 3.52x | - | PCIe 15 ns/read; QC share of process 99% |
| B GPU-resident, QC 121x (measured kernel) | 6.4 | 0.0 | 126.9 | 126.4 | 0.30x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a5, ratio 5.12 vs libdeflate 5.17 |
| C fused into GPU aligner, QC 121x (measured kernel) | 0.0 | -17.9 | 3.3 | 3.3 | 11.25x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 208.0 | -53.5 | 134.6 | 134.6 | 0.28x | - | PCIe 15 ns/read; QC share of process 99% |
| B GPU-resident, QC 3x (assumed) | 6.4 | 0.0 | 257.9 | 257.4 | 0.15x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a5, ratio 5.12 vs libdeflate 5.17 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -17.9 | 134.3 | 134.3 | 0.28x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 208.0 | -53.5 | 41.0 | 41.0 | 0.91x | - | PCIe 15 ns/read; QC share of process 99% |
| B GPU-resident, QC 10x (assumed) | 6.4 | 0.0 | 163.9 | 163.4 | 0.23x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a5, ratio 5.12 vs libdeflate 5.17 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -17.9 | 40.3 | 40.3 | 0.93x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
