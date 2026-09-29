# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **39.71 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.16 s, worker_wait 0.23 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read-L | 1 | 0.0 | 5.6 | 0.0 | 0.0 | 20.0 | 13.5 | 0.0 | 0.0 | 64% | 34% |
| fp-read-R | 1 | 0.0 | 10.7 | 0.0 | 0.0 | 25.3 | 3.0 | 0.0 | 0.0 | 91% | 8% |
| fp-work | 16 | 155.5 | 0.0 | 2.8 | 323.5 | 0.0 | 0.0 | 151.0 | 2.4 | 76% | 24% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 56,760,748 over 2 input(s) (28,380,374 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 286 | 16.3 | 1216 MB/s per thread |
| parse into Read objects | reader | 799 | 45.4 | 436 MB/s per thread |
| trim/filter/stats/serialise | workers | 5699 | 323.5 | - |
| compress (libdeflate) | workers or writer | 2739 | 155.5 | 127 MB/s per thread in, ratio 5.17 |
| write | workers or writer | 42 | 2.4 | - |

Per-read work (trim/filter/stats) is **60%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|
| 0.0 | 63% / 36% | 89% / 9% | 75% / 25% |
| 2.0 | 64% / 35% | 90% / 9% | 76% / 24% |
| 4.0 | 65% / 34% | 90% / 8% | 76% / 24% |
| 6.0 | 66% / 33% | 92% / 7% | 75% / 25% |
| 7.9 | 63% / 35% | 91% / 8% | 76% / 24% |
| 9.9 | 65% / 34% | 90% / 9% | 76% / 24% |
| 11.9 | 62% / 36% | 90% / 8% | 74% / 26% |
| 13.9 | 63% / 36% | 86% / 12% | 77% / 23% |
| 15.9 | 65% / 33% | 92% / 6% | 77% / 24% |
| 17.9 | 63% / 35% | 93% / 6% | 76% / 24% |
| 19.9 | 66% / 32% | 92% / 7% | 76% / 24% |
| 21.8 | 66% / 32% | 91% / 7% | 76% / 24% |
| 23.8 | 66% / 32% | 93% / 6% | 76% / 24% |
| 25.8 | 64% / 35% | 90% / 8% | 75% / 25% |
| 27.8 | 66% / 32% | 92% / 7% | 76% / 24% |
| 29.8 | 65% / 34% | 93% / 5% | 75% / 25% |
| 31.8 | 68% / 31% | 91% / 7% | 76% / 24% |
| 33.7 | 61% / 37% | 90% / 9% | 76% / 23% |
| 35.7 | 64% / 35% | 92% / 7% | 76% / 24% |
| 37.7 | 64% / 33% | 89% / 7% | 76% / 23% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 18, p95 20, max 23 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Reader-bound**: the busiest reader is 91% busy while workers wait 24% of the time. More workers or faster per-read code will not help; faster/parallel decompression and parsing would.

