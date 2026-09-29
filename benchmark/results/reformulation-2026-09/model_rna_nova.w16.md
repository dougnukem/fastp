# Reformulation projection

Sample: 31,039,057 reads per mate x 2 mate(s); CPU box 48 vCPUs, fastp -w 16.
Measured per read (trace): decompress 300 ns, parse 783, process 9380, compress 2714, write 131. Transforms (soa_pack): index 33, pack 37, emit 46, CPU kernel 1163.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 826.1 | 0.0 | 0.0 | 47.4 | 1.00x | - | reader 34s vs workers 47s |
| D1 BGZF input | 826.1 | 360.5 | 0.0 | 47.4 | 1.00x | - | pool 14 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 911.5 | 0.0 | 0.0 | 47.4 | 1.00x | - | CPU/byte x5.58 vs ISA-L (from codec baselines) |
| D3 -z 1 | 739.0 | 0.0 | 0.0 | 42.0 | 1.13x | - | compress x2.1 faster, output larger |
| D4 uncompressed stream to aligner | 657.6 | -18.6 | 0.0 | 36.9 | 1.29x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 781.9 | -44.2 | 0.0 | 47.4 | 1.00x | - | reader 11s vs workers 47s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 209x (measured kernel) | 202.4 | -44.2 | 4.3 | 11.5 | 4.13x | - | PCIe 25 ns/read; QC share of process 100% |
| B GPU-resident, QC 209x (measured kernel) | 11.2 | 0.0 | 30.1 | 29.4 | 1.61x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.87 |
| C fused into GPU aligner, QC 209x (measured kernel) | 0.0 | -18.6 | 2.8 | 2.8 | 17.01x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 202.4 | -44.2 | 194.7 | 194.7 | 0.24x | - | PCIe 25 ns/read; QC share of process 100% |
| B GPU-resident, QC 3x (assumed) | 11.2 | 0.0 | 221.1 | 220.4 | 0.22x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.87 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -18.6 | 193.8 | 193.8 | 0.24x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 202.4 | -44.2 | 59.5 | 59.5 | 0.80x | - | PCIe 25 ns/read; QC share of process 100% |
| B GPU-resident, QC 10x (assumed) | 11.2 | 0.0 | 85.4 | 84.8 | 0.56x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.87 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -18.6 | 58.2 | 58.2 | 0.82x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
