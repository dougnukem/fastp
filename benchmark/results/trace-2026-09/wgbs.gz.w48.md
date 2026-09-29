# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **48.16 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.16 s, worker_wait 0.72 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read-L | 1 | 0.0 | 6.1 | 0.0 | 0.0 | 24.9 | 12.9 | 0.0 | 0.0 | 64% | 27% |
| fp-read-R | 1 | 0.0 | 11.8 | 0.0 | 0.0 | 32.0 | 0.0 | 0.0 | 0.0 | 91% | 0% |
| fp-work | 48 | 181.1 | 0.0 | 37.3 | 403.3 | 0.0 | 0.0 | 1684.4 | 3.5 | 25% | 74% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 56,760,748 over 2 input(s) (28,380,374 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 315 | 17.9 | 1105 MB/s per thread |
| parse into Read objects | reader | 1001 | 56.8 | 348 MB/s per thread |
| trim/filter/stats/serialise | workers | 7105 | 403.3 | - |
| compress (libdeflate) | workers or writer | 3190 | 181.1 | 109 MB/s per thread in, ratio 5.17 |
| write | workers or writer | 62 | 3.5 | - |

Per-read work (trim/filter/stats) is **61%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|
| 0.0 | 58% / 32% | 90% / 0% | 23% / 77% |
| 2.4 | 61% / 31% | 91% / 0% | 25% / 75% |
| 4.8 | 63% / 29% | 91% / 0% | 24% / 76% |
| 7.2 | 65% / 27% | 91% / 0% | 25% / 75% |
| 9.6 | 65% / 27% | 90% / 0% | 26% / 73% |
| 12.0 | 69% / 22% | 91% / 0% | 27% / 73% |
| 14.4 | 67% / 24% | 91% / 0% | 26% / 74% |
| 16.9 | 69% / 22% | 91% / 0% | 26% / 74% |
| 19.3 | 70% / 21% | 91% / 0% | 26% / 74% |
| 21.7 | 67% / 25% | 91% / 0% | 28% / 72% |
| 24.1 | 66% / 26% | 91% / 0% | 26% / 74% |
| 26.5 | 68% / 24% | 92% / 0% | 27% / 73% |
| 28.9 | 63% / 29% | 91% / 0% | 25% / 75% |
| 31.3 | 66% / 26% | 91% / 0% | 25% / 75% |
| 33.7 | 62% / 30% | 91% / 0% | 24% / 76% |
| 36.1 | 65% / 27% | 91% / 0% | 24% / 76% |
| 38.5 | 63% / 28% | 91% / 0% | 25% / 75% |
| 40.9 | 63% / 29% | 91% / 0% | 24% / 76% |
| 43.3 | 62% / 30% | 91% / 0% | 24% / 76% |
| 45.8 | 57% / 26% | 85% / 0% | 28% / 71% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 65, p95 68, max 70 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Reader-bound**: the busiest reader is 91% busy while workers wait 74% of the time. More workers or faster per-read code will not help; faster/parallel decompression and parsing would.

