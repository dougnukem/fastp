# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **52.13 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.29 s, bgzf_fetch 0.08 s, worker_wait 0.44 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 2 | 31.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 30% | 0% |
| fp-read-L | 1 | 0.0 | 14.0 | 0.0 | 0.0 | 0.0 | 33.6 | 0.3 | 0.0 | 0.0 | 65% | 27% |
| fp-read-R | 1 | 0.0 | 14.1 | 0.0 | 0.0 | 0.0 | 33.5 | 0.3 | 0.0 | 0.0 | 64% | 28% |
| fp-work | 48 | 0.0 | 0.0 | 214.1 | 102.1 | 806.9 | 0.0 | 0.0 | 1372.1 | 4.3 | 41% | 59% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 62,078,114 over 2 input(s) (31,039,057 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 452 | 28.0 | - |
| BGZF block inflate | fp-bgzf pool | 501 | 31.1 | 671 MB/s per thread |
| parse into Read objects | reader | 1082 | 67.2 | 311 MB/s per thread |
| trim/filter/stats/serialise | workers | 12998 | 806.9 | - |
| compress (libdeflate) | workers or writer | 3449 | 214.1 | 97 MB/s per thread in, ratio 4.87 |
| write | workers or writer | 69 | 4.3 | - |

Per-read work (trim/filter/stats) is **72%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|---|
| 0.0 | 30% / 0% | 62% / 27% | 61% / 28% | 39% / 61% |
| 2.6 | 30% / 0% | 65% / 27% | 62% / 29% | 41% / 59% |
| 5.2 | 31% / 0% | 64% / 28% | 63% / 30% | 44% / 56% |
| 7.8 | 31% / 0% | 64% / 28% | 64% / 29% | 42% / 58% |
| 10.4 | 31% / 0% | 64% / 28% | 64% / 29% | 44% / 56% |
| 13.0 | 31% / 0% | 63% / 29% | 65% / 27% | 43% / 57% |
| 15.6 | 30% / 0% | 66% / 27% | 64% / 29% | 42% / 58% |
| 18.2 | 31% / 0% | 65% / 27% | 64% / 29% | 40% / 60% |
| 20.9 | 29% / 0% | 65% / 26% | 65% / 27% | 40% / 60% |
| 23.5 | 29% / 0% | 65% / 27% | 66% / 27% | 43% / 57% |
| 26.1 | 30% / 0% | 63% / 30% | 66% / 27% | 40% / 60% |
| 28.7 | 29% / 0% | 65% / 27% | 66% / 27% | 41% / 59% |
| 31.3 | 30% / 0% | 65% / 27% | 65% / 28% | 41% / 59% |
| 33.9 | 30% / 0% | 65% / 28% | 65% / 28% | 41% / 59% |
| 36.5 | 29% / 0% | 65% / 27% | 65% / 27% | 40% / 60% |
| 39.1 | 30% / 0% | 65% / 27% | 65% / 27% | 40% / 60% |
| 41.7 | 29% / 0% | 66% / 26% | 65% / 27% | 39% / 61% |
| 44.3 | 29% / 0% | 65% / 27% | 66% / 26% | 40% / 60% |
| 46.9 | 30% / 0% | 65% / 28% | 66% / 27% | 40% / 60% |
| 49.5 | 28% / 0% | 62% / 26% | 62% / 25% | 42% / 57% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 55, p95 60, max 63 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Mixed**: busiest reader 65%, workers busy 41% / waiting 59%. Check the timeline for phases.

