# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **53.03 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.08 s, worker_wait 0.69 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read | 1 | 0.0 | 8.3 | 0.0 | 0.0 | 38.1 | 0.0 | 0.0 | 0.0 | 87% | 0% |
| fp-work | 48 | 81.4 | 0.0 | 8.2 | 271.5 | 0.0 | 0.0 | 2180.9 | 1.9 | 14% | 86% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 42,623,602 over 1 input(s) (42,623,602 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 194 | 8.3 | 1123 MB/s per thread |
| parse into Read objects | reader | 893 | 38.1 | 244 MB/s per thread |
| trim/filter/stats/serialise | workers | 6369 | 271.5 | - |
| compress (libdeflate) | workers or writer | 1911 | 81.4 | 112 MB/s per thread in, ratio 4.75 |
| write | workers or writer | 44 | 1.9 | - |

Per-read work (trim/filter/stats) is **68%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read | fp-work |
|---|---|---|
| 0.0 | 87% / 0% | 14% / 86% |
| 2.7 | 87% / 0% | 13% / 87% |
| 5.3 | 88% / 0% | 13% / 87% |
| 8.0 | 88% / 0% | 15% / 85% |
| 10.6 | 88% / 0% | 14% / 86% |
| 13.3 | 88% / 0% | 15% / 85% |
| 15.9 | 88% / 0% | 14% / 86% |
| 18.6 | 87% / 0% | 14% / 86% |
| 21.2 | 88% / 0% | 14% / 86% |
| 23.9 | 87% / 0% | 15% / 85% |
| 26.5 | 88% / 0% | 14% / 86% |
| 29.2 | 88% / 0% | 13% / 87% |
| 31.8 | 87% / 0% | 13% / 87% |
| 34.5 | 87% / 0% | 13% / 87% |
| 37.1 | 88% / 0% | 14% / 86% |
| 39.8 | 88% / 0% | 14% / 86% |
| 42.4 | 87% / 0% | 13% / 87% |
| 45.1 | 87% / 0% | 14% / 86% |
| 47.7 | 87% / 0% | 14% / 86% |
| 50.4 | 85% / 0% | 15% / 84% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 48, p95 49, max 50 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Reader-bound**: the busiest reader is 87% busy while workers wait 86% of the time. More workers or faster per-read code will not help; faster/parallel decompression and parsing would.

