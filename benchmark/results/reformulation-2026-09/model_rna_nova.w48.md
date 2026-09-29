# Reformulation projection

Sample: 31,039,057 reads per mate x 2 mate(s); CPU box 48 vCPUs, fastp -w 48.
Measured per read (trace): decompress 344 ns, parse 1103, process 13188, compress 3461, write 270. Transforms (soa_pack): index 33, pack 37, emit 46, CPU kernel 1163.

| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |
|---|---|---|---|---|---|---|---|
| base | 1140.1 | 0.0 | 0.0 | 44.9 | 1.00x | - | reader 45s vs workers 22s |
| D1 BGZF input | 1140.1 | 360.5 | 0.0 | 44.9 | 1.00x | - | pool 1 thr/mate; transform = gunzip + bgzip once, only if input isn't BGZF already |
| D2 parallel gzip reader | 1238.0 | 0.0 | 0.0 | 93.9 | 0.48x | - | CPU/byte x5.58 vs ISA-L (from codec baselines) |
| D3 -z 1 | 1029.0 | 0.0 | 0.0 | 44.9 | 1.00x | - | compress x2.1 faster, output larger |
| D4 uncompressed stream to aligner | 925.3 | -21.3 | 0.0 | 44.9 | 1.00x | - | no output compression; negative transform = downstream inflate avoided |
| D5 flat-batch parser (CPU) | 1076.0 | -64.2 | 0.0 | 21.9 | 2.05x | - | reader 13s vs workers 22s; transform < 0 = parse CPU saved |
| A offload per-read QC, QC 209x (measured kernel) | 260.1 | -64.2 | 5.5 | 12.9 | 3.50x | - | PCIe 25 ns/read; QC share of process 100% |
| B GPU-resident, QC 209x (measured kernel) | 19.8 | 0.0 | 31.2 | 30.5 | 1.47x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.87 |
| C fused into GPU aligner, QC 209x (measured kernel) | 0.0 | -21.3 | 3.9 | 3.9 | 11.45x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 3x (assumed) | 260.1 | -64.2 | 273.5 | 273.5 | 0.16x | - | PCIe 25 ns/read; QC share of process 100% |
| B GPU-resident, QC 3x (assumed) | 19.8 | 0.0 | 299.9 | 299.2 | 0.15x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.87 |
| C fused into GPU aligner, QC 3x (assumed) | 0.0 | -21.3 | 272.6 | 272.6 | 0.16x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |
| A offload per-read QC, QC 10x (assumed) | 260.1 | -64.2 | 83.1 | 83.1 | 0.54x | - | PCIe 25 ns/read; QC share of process 100% |
| B GPU-resident, QC 10x (assumed) | 19.8 | 0.0 | 109.1 | 108.4 | 0.41x | - | inflate: single-stream gzip (nvlzcat); compress: nvlzcat-gzip/a2, ratio 4.61 vs libdeflate 4.87 |
| C fused into GPU aligner, QC 10x (assumed) | 0.0 | -21.3 | 81.8 | 81.8 | 0.55x | - | fastp CPU work disappears; negative transform = downstream re-read avoided |

Wall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed pre/detect stages from full-size.md. CPU s is summed across threads.
- A/B/C: "measured kernel" applies the analogue kernel's CPU/GPU speedup to all of fastp's QC work (process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats and per-read string handling that may not speed up as much; the "assumed" rows bracket that.
- B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan divided by the speedup.
- C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).
