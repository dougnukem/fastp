# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **259.13 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.15 s, worker_wait 0.81 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read-L | 1 | 0.0 | 36.9 | 0.0 | 0.0 | 191.5 | 1.8 | 0.0 | 0.0 | 88% | 1% |
| fp-read-R | 1 | 0.0 | 37.9 | 0.0 | 0.0 | 181.6 | 10.0 | 0.0 | 0.0 | 85% | 4% |
| fp-work | 48 | 701.0 | 0.0 | 84.2 | 1862.7 | 0.0 | 0.0 | 9743.6 | 39.9 | 21% | 79% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 385,809,298 over 2 input(s) (192,904,649 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 194 | 74.8 | 871 MB/s per thread |
| parse into Read objects | reader | 967 | 373.1 | 175 MB/s per thread |
| trim/filter/stats/serialise | workers | 4828 | 1862.7 | - |
| compress (libdeflate) | workers or writer | 1817 | 701.0 | 90 MB/s per thread in, ratio 3.64 |
| write | workers or writer | 103 | 39.9 | - |

Per-read work (trim/filter/stats) is **61%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|
| 0.0 | 86% / 1% | 84% / 3% | 23% / 77% |
| 13.0 | 88% / 0% | 83% / 5% | 21% / 78% |
| 25.9 | 88% / 0% | 83% / 5% | 22% / 78% |
| 38.9 | 87% / 1% | 86% / 2% | 23% / 77% |
| 51.8 | 88% / 1% | 87% / 1% | 22% / 78% |
| 64.8 | 88% / 0% | 87% / 1% | 22% / 78% |
| 77.7 | 87% / 2% | 86% / 2% | 21% / 79% |
| 90.7 | 88% / 1% | 88% / 1% | 21% / 79% |
| 103.7 | 89% / 0% | 85% / 4% | 21% / 79% |
| 116.6 | 88% / 1% | 86% / 3% | 20% / 80% |
| 129.6 | 87% / 2% | 85% / 4% | 22% / 78% |
| 142.5 | 89% / 0% | 83% / 6% | 20% / 80% |
| 155.5 | 89% / 0% | 83% / 6% | 20% / 80% |
| 168.4 | 89% / 0% | 84% / 4% | 20% / 80% |
| 181.4 | 89% / 0% | 86% / 3% | 20% / 80% |
| 194.3 | 89% / 0% | 82% / 7% | 19% / 81% |
| 207.3 | 89% / 0% | 82% / 7% | 19% / 81% |
| 220.3 | 88% / 2% | 79% / 11% | 20% / 80% |
| 233.2 | 89% / 1% | 87% / 2% | 20% / 80% |
| 246.2 | 87% / 1% | 88% / 0% | 21% / 79% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 64, p95 68, max 73 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Reader-bound**: the busiest reader is 88% busy while workers wait 79% of the time. More workers or faster per-read code will not help; faster/parallel decompression and parsing would.

