# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **49.86 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.20 s, worker_wait 0.75 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read-L | 1 | 0.0 | 10.6 | 0.0 | 0.0 | 33.6 | 2.0 | 0.0 | 0.0 | 89% | 4% |
| fp-read-R | 1 | 0.0 | 10.8 | 0.0 | 0.0 | 34.9 | 0.3 | 0.0 | 0.0 | 92% | 1% |
| fp-work | 48 | 214.8 | 0.0 | 99.3 | 818.7 | 0.0 | 0.0 | 1241.3 | 16.7 | 44% | 56% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 62,078,114 over 2 input(s) (31,039,057 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 344 | 21.4 | 977 MB/s per thread |
| parse into Read objects | reader | 1103 | 68.5 | 305 MB/s per thread |
| trim/filter/stats/serialise | workers | 13188 | 818.7 | - |
| compress (libdeflate) | workers or writer | 3461 | 214.8 | 96 MB/s per thread in, ratio 4.87 |
| write | workers or writer | 270 | 16.7 | - |

Per-read work (trim/filter/stats) is **72%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|
| 0.0 | 91% / 0% | 90% / 1% | 43% / 57% |
| 2.5 | 87% / 5% | 93% / 0% | 46% / 54% |
| 5.0 | 89% / 3% | 92% / 0% | 46% / 54% |
| 7.5 | 87% / 6% | 93% / 0% | 46% / 54% |
| 10.0 | 89% / 5% | 93% / 0% | 45% / 55% |
| 12.5 | 91% / 2% | 92% / 0% | 47% / 53% |
| 15.0 | 86% / 7% | 93% / 0% | 44% / 56% |
| 17.5 | 90% / 3% | 93% / 0% | 45% / 55% |
| 19.9 | 88% / 5% | 93% / 0% | 43% / 57% |
| 22.4 | 87% / 6% | 93% / 0% | 43% / 57% |
| 24.9 | 91% / 3% | 93% / 0% | 42% / 58% |
| 27.4 | 93% / 0% | 92% / 1% | 41% / 59% |
| 29.9 | 92% / 0% | 92% / 1% | 43% / 57% |
| 32.4 | 88% / 5% | 92% / 0% | 42% / 58% |
| 34.9 | 80% / 13% | 82% / 10% | 49% / 51% |
| 37.4 | 90% / 2% | 92% / 0% | 44% / 56% |
| 39.9 | 87% / 6% | 92% / 0% | 42% / 58% |
| 42.4 | 91% / 2% | 93% / 0% | 42% / 58% |
| 44.9 | 91% / 2% | 92% / 0% | 42% / 58% |
| 47.4 | 84% / 3% | 87% / 0% | 44% / 55% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 58, p95 61, max 65 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Reader-bound**: the busiest reader is 92% busy while workers wait 56% of the time. More workers or faster per-read code will not help; faster/parallel decompression and parsing would.

