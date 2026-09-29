# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **49.64 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.22 s, bgzf_fetch 0.07 s, worker_wait 0.34 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 2 | 24.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 24% | 0% |
| fp-read-L | 1 | 0.0 | 7.1 | 0.0 | 0.0 | 0.0 | 26.6 | 11.6 | 0.0 | 0.0 | 54% | 38% |
| fp-read-R | 1 | 0.0 | 14.8 | 0.0 | 0.0 | 0.0 | 30.4 | 0.0 | 0.0 | 0.0 | 61% | 30% |
| fp-work | 48 | 0.0 | 0.0 | 182.6 | 38.8 | 407.7 | 0.0 | 0.0 | 1747.8 | 3.5 | 25% | 75% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 56,760,748 over 2 input(s) (28,380,374 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 387 | 22.0 | - |
| BGZF block inflate | fp-bgzf pool | 427 | 24.2 | 816 MB/s per thread |
| parse into Read objects | reader | 1006 | 57.1 | 346 MB/s per thread |
| trim/filter/stats/serialise | workers | 7182 | 407.7 | - |
| compress (libdeflate) | workers or writer | 3217 | 182.6 | 108 MB/s per thread in, ratio 5.17 |
| write | workers or writer | 62 | 3.5 | - |

Per-read work (trim/filter/stats) is **60%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|---|
| 0.0 | 25% / 0% | 48% / 41% | 59% / 30% | 23% / 77% |
| 2.5 | 24% / 0% | 56% / 36% | 62% / 30% | 26% / 74% |
| 5.0 | 24% / 0% | 57% / 34% | 63% / 28% | 25% / 75% |
| 7.4 | 25% / 0% | 56% / 36% | 62% / 30% | 26% / 74% |
| 9.9 | 25% / 0% | 54% / 38% | 61% / 31% | 27% / 73% |
| 12.4 | 24% / 0% | 57% / 35% | 62% / 30% | 24% / 76% |
| 14.9 | 25% / 0% | 54% / 38% | 61% / 31% | 24% / 76% |
| 17.4 | 24% / 0% | 55% / 37% | 61% / 30% | 25% / 75% |
| 19.9 | 25% / 0% | 55% / 37% | 61% / 31% | 25% / 75% |
| 22.3 | 25% / 0% | 53% / 39% | 60% / 32% | 25% / 75% |
| 24.8 | 26% / 0% | 56% / 36% | 60% / 31% | 25% / 75% |
| 27.3 | 24% / 0% | 56% / 36% | 62% / 30% | 25% / 75% |
| 29.8 | 25% / 0% | 53% / 39% | 61% / 30% | 25% / 75% |
| 32.3 | 24% / 0% | 53% / 39% | 61% / 30% | 25% / 75% |
| 34.7 | 24% / 0% | 53% / 39% | 62% / 29% | 24% / 75% |
| 37.2 | 24% / 0% | 53% / 39% | 63% / 29% | 24% / 76% |
| 39.7 | 24% / 0% | 51% / 41% | 62% / 29% | 24% / 76% |
| 42.2 | 24% / 0% | 55% / 37% | 63% / 29% | 25% / 75% |
| 44.7 | 24% / 0% | 50% / 42% | 62% / 30% | 23% / 76% |
| 47.2 | 22% / 0% | 48% / 36% | 58% / 27% | 28% / 71% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 65, p95 68, max 70 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Mixed**: busiest reader 61%, workers busy 25% / waiting 75%. Check the timeline for phases.

