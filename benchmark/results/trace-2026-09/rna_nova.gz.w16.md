# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **52.40 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): decompress 0.20 s, worker_wait 0.23 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | compress | decompress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-read-L | 1 | 0.0 | 9.3 | 0.0 | 0.0 | 25.0 | 17.7 | 0.0 | 0.0 | 65% | 34% |
| fp-read-R | 1 | 0.0 | 9.4 | 0.0 | 0.0 | 23.6 | 19.1 | 0.0 | 0.0 | 63% | 36% |
| fp-work | 16 | 168.5 | 0.0 | 2.7 | 582.3 | 0.0 | 0.0 | 76.6 | 8.1 | 91% | 9% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 62,078,114 over 2 input(s) (31,039,057 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| decompress (ordinary gzip) | reader | 300 | 18.6 | 1120 MB/s per thread |
| parse into Read objects | reader | 783 | 48.6 | 430 MB/s per thread |
| trim/filter/stats/serialise | workers | 9380 | 582.3 | - |
| compress (libdeflate) | workers or writer | 2714 | 168.5 | 123 MB/s per thread in, ratio 4.87 |
| write | workers or writer | 131 | 8.1 | - |

Per-read work (trim/filter/stats) is **70%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|
| 0.0 | 64% / 35% | 59% / 40% | 87% / 13% |
| 2.6 | 63% / 36% | 62% / 37% | 90% / 10% |
| 5.2 | 62% / 37% | 63% / 36% | 91% / 9% |
| 7.9 | 63% / 37% | 62% / 37% | 90% / 10% |
| 10.5 | 64% / 35% | 61% / 38% | 91% / 9% |
| 13.1 | 64% / 36% | 64% / 36% | 91% / 9% |
| 15.7 | 63% / 36% | 62% / 37% | 91% / 9% |
| 18.3 | 65% / 34% | 64% / 35% | 92% / 8% |
| 21.0 | 66% / 33% | 64% / 35% | 91% / 9% |
| 23.6 | 64% / 35% | 65% / 34% | 91% / 9% |
| 26.2 | 65% / 34% | 66% / 34% | 91% / 9% |
| 28.8 | 67% / 33% | 65% / 35% | 91% / 9% |
| 31.4 | 57% / 42% | 55% / 44% | 90% / 10% |
| 34.1 | 67% / 32% | 65% / 34% | 91% / 9% |
| 36.7 | 69% / 30% | 66% / 33% | 91% / 9% |
| 39.3 | 68% / 31% | 64% / 36% | 89% / 11% |
| 41.9 | 69% / 31% | 62% / 37% | 91% / 9% |
| 44.5 | 70% / 29% | 63% / 37% | 91% / 9% |
| 47.2 | 69% / 30% | 63% / 37% | 90% / 9% |
| 49.8 | 69% / 28% | 62% / 35% | 90% / 9% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 17, p95 18, max 24 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Worker-bound**: workers are 91% busy. Per-read work or compression is the critical path.

