# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **269.25 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.19 s, bgzf_fetch 0.06 s, worker_wait 0.44 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 2 | 91.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 17% | 0% |
| fp-read-L | 1 | 0.0 | 40.9 | 0.0 | 0.0 | 0.0 | 190.4 | 8.3 | 0.0 | 0.0 | 71% | 18% |
| fp-read-R | 1 | 0.0 | 41.8 | 0.0 | 0.0 | 0.0 | 193.9 | 3.9 | 0.0 | 0.0 | 72% | 17% |
| fp-work | 48 | 0.0 | 0.0 | 701.1 | 82.4 | 1886.3 | 0.0 | 0.0 | 10210.2 | 36.1 | 20% | 80% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 385,809,298 over 2 input(s) (192,904,649 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 214 | 82.7 | - |
| BGZF block inflate | fp-bgzf pool | 237 | 91.6 | 711 MB/s per thread |
| parse into Read objects | reader | 996 | 384.3 | 170 MB/s per thread |
| trim/filter/stats/serialise | workers | 4889 | 1886.3 | - |
| compress (libdeflate) | workers or writer | 1817 | 701.1 | 90 MB/s per thread in, ratio 3.64 |
| write | workers or writer | 94 | 36.1 | - |

Per-read work (trim/filter/stats) is **61%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|---|
| 0.0 | 19% / 0% | 70% / 19% | 68% / 20% | 23% / 77% |
| 13.5 | 18% / 0% | 72% / 17% | 68% / 20% | 20% / 80% |
| 26.9 | 18% / 0% | 73% / 16% | 66% / 23% | 21% / 79% |
| 40.4 | 18% / 0% | 71% / 17% | 71% / 18% | 20% / 80% |
| 53.9 | 18% / 0% | 66% / 23% | 73% / 16% | 20% / 80% |
| 67.3 | 17% / 0% | 71% / 18% | 73% / 16% | 21% / 79% |
| 80.8 | 17% / 0% | 66% / 24% | 74% / 15% | 20% / 80% |
| 94.2 | 17% / 0% | 67% / 22% | 74% / 16% | 20% / 80% |
| 107.7 | 17% / 0% | 71% / 18% | 73% / 16% | 20% / 80% |
| 121.2 | 17% / 0% | 73% / 16% | 72% / 17% | 20% / 80% |
| 134.6 | 17% / 0% | 74% / 15% | 72% / 17% | 20% / 80% |
| 148.1 | 17% / 0% | 72% / 17% | 73% / 16% | 20% / 80% |
| 161.6 | 17% / 0% | 72% / 17% | 73% / 16% | 20% / 80% |
| 175.0 | 16% / 0% | 74% / 15% | 72% / 17% | 20% / 80% |
| 188.5 | 17% / 0% | 74% / 15% | 73% / 17% | 20% / 80% |
| 201.9 | 17% / 0% | 73% / 16% | 72% / 17% | 20% / 80% |
| 215.4 | 16% / 0% | 70% / 19% | 74% / 15% | 20% / 80% |
| 228.9 | 16% / 0% | 67% / 23% | 72% / 18% | 22% / 78% |
| 242.3 | 17% / 0% | 70% / 19% | 74% / 15% | 20% / 80% |
| 255.8 | 16% / 0% | 70% / 18% | 73% / 15% | 20% / 80% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 62, p95 68, max 72 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Mixed**: busiest reader 72%, workers busy 20% / waiting 80%. Check the timeline for phases.

