# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **41.37 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.08 s, worker_wait 0.22 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read | 1 | 0.0 | 7.9 | 0.0 | 0.0 | 32.0 | 0.0 | 0.0 | 0.0 | 96% | 0% |
| fp-work | 16 | 73.1 | 0.0 | 1.6 | 229.6 | 0.0 | 0.0 | 355.9 | 1.5 | 46% | 54% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 42,623,602 over 1 input(s) (42,623,602 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 184 | 7.9 | 1182 MB/s per thread |
| parse into Read objects | reader | 751 | 32.0 | 290 MB/s per thread |
| trim/filter/stats/serialise | workers | 5387 | 229.6 | - |
| compress (libdeflate) | workers or writer | 1715 | 73.1 | 125 MB/s per thread in, ratio 4.75 |
| write | workers or writer | 36 | 1.5 | - |

Per-read work (trim/filter/stats) is **67%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read | fp-work |
|---|---|---|
| 0.0 | 97% / 0% | 53% / 47% |
| 2.1 | 96% / 0% | 50% / 50% |
| 4.1 | 97% / 0% | 51% / 49% |
| 6.2 | 97% / 0% | 50% / 50% |
| 8.3 | 96% / 0% | 49% / 51% |
| 10.3 | 96% / 0% | 46% / 54% |
| 12.4 | 96% / 0% | 44% / 56% |
| 14.5 | 96% / 0% | 44% / 56% |
| 16.5 | 96% / 0% | 44% / 56% |
| 18.6 | 96% / 0% | 43% / 57% |
| 20.7 | 96% / 0% | 44% / 56% |
| 22.8 | 97% / 0% | 47% / 53% |
| 24.8 | 96% / 0% | 44% / 56% |
| 26.9 | 96% / 0% | 44% / 56% |
| 29.0 | 96% / 0% | 44% / 56% |
| 31.0 | 96% / 0% | 45% / 55% |
| 33.1 | 96% / 0% | 45% / 55% |
| 35.2 | 96% / 0% | 45% / 55% |
| 37.2 | 96% / 0% | 44% / 56% |
| 39.3 | 96% / 0% | 44% / 55% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 16, p95 17, max 18 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Reader-bound**: the busiest reader is 96% busy while workers wait 54% of the time. More workers or faster per-read code will not help; faster/parallel decompression and parsing would.

