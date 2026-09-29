# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **188.58 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.15 s, worker_wait 0.25 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read-L | 1 | 0.0 | 34.2 | 0.0 | 0.0 | 134.2 | 16.3 | 0.0 | 0.0 | 89% | 9% |
| fp-read-R | 1 | 0.0 | 35.1 | 0.0 | 0.0 | 124.9 | 24.7 | 0.0 | 0.0 | 85% | 13% |
| fp-work | 16 | 605.8 | 0.0 | 7.8 | 1518.3 | 0.0 | 0.0 | 867.5 | 17.2 | 71% | 29% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 385,809,298 over 2 input(s) (192,904,649 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 180 | 69.4 | 939 MB/s per thread |
| parse into Read objects | reader | 672 | 259.2 | 251 MB/s per thread |
| trim/filter/stats/serialise | workers | 3935 | 1518.3 | - |
| compress (libdeflate) | workers or writer | 1570 | 605.8 | 104 MB/s per thread in, ratio 3.64 |
| write | workers or writer | 45 | 17.2 | - |

Per-read work (trim/filter/stats) is **61%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|
| 0.0 | 92% / 6% | 76% / 22% | 68% / 32% |
| 9.4 | 91% / 7% | 80% / 18% | 72% / 28% |
| 18.9 | 92% / 5% | 80% / 18% | 70% / 29% |
| 28.3 | 88% / 10% | 87% / 11% | 73% / 27% |
| 37.7 | 91% / 7% | 84% / 14% | 73% / 27% |
| 47.1 | 94% / 4% | 81% / 17% | 68% / 32% |
| 56.6 | 88% / 9% | 87% / 10% | 68% / 31% |
| 66.0 | 84% / 14% | 90% / 8% | 71% / 29% |
| 75.4 | 85% / 13% | 88% / 10% | 71% / 29% |
| 84.9 | 90% / 8% | 85% / 13% | 70% / 30% |
| 94.3 | 89% / 9% | 85% / 13% | 71% / 29% |
| 103.7 | 88% / 10% | 83% / 15% | 71% / 29% |
| 113.1 | 89% / 9% | 85% / 13% | 71% / 29% |
| 122.6 | 90% / 8% | 88% / 10% | 72% / 28% |
| 132.0 | 92% / 6% | 87% / 11% | 73% / 27% |
| 141.4 | 91% / 7% | 84% / 14% | 72% / 28% |
| 150.9 | 89% / 9% | 86% / 12% | 72% / 28% |
| 160.3 | 90% / 8% | 86% / 12% | 71% / 29% |
| 169.7 | 88% / 10% | 83% / 15% | 71% / 29% |
| 179.2 | 86% / 12% | 91% / 6% | 71% / 29% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 18, p95 22, max 25 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Reader-bound**: the busiest reader is 89% busy while workers wait 29% of the time. More workers or faster per-read code will not help; faster/parallel decompression and parsing would.

