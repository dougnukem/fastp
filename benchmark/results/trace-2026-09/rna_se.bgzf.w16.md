# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **43.99 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.11 s, bgzf_fetch 0.04 s, worker_wait 0.18 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 29 | 14.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1% | 0% |
| fp-read | 1 | 0.0 | 7.9 | 0.0 | 0.0 | 0.0 | 34.6 | 0.1 | 0.0 | 0.0 | 79% | 18% |
| fp-work | 16 | 0.0 | 0.0 | 81.0 | 12.6 | 256.1 | 0.0 | 0.0 | 352.1 | 1.8 | 48% | 52% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 42,623,602 over 1 input(s) (42,623,602 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 184 | 7.9 | - |
| BGZF block inflate | fp-bgzf pool | 334 | 14.2 | 652 MB/s per thread |
| parse into Read objects | reader | 812 | 34.6 | 268 MB/s per thread |
| trim/filter/stats/serialise | workers | 6008 | 256.1 | - |
| compress (libdeflate) | workers or writer | 1899 | 81.0 | 113 MB/s per thread in, ratio 4.75 |
| write | workers or writer | 43 | 1.8 | - |

Per-read work (trim/filter/stats) is **66%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read | fp-work |
|---|---|---|---|
| 0.0 | 1% / 0% | 80% / 17% | 46% / 54% |
| 2.2 | 1% / 0% | 78% / 19% | 49% / 51% |
| 4.4 | 1% / 0% | 79% / 18% | 49% / 51% |
| 6.6 | 1% / 0% | 78% / 19% | 53% / 47% |
| 8.8 | 1% / 0% | 78% / 19% | 50% / 49% |
| 11.0 | 1% / 0% | 78% / 19% | 48% / 52% |
| 13.2 | 1% / 0% | 78% / 19% | 50% / 50% |
| 15.4 | 1% / 0% | 78% / 19% | 50% / 50% |
| 17.6 | 1% / 0% | 79% / 18% | 46% / 54% |
| 19.8 | 1% / 0% | 78% / 18% | 46% / 54% |
| 22.0 | 1% / 0% | 79% / 18% | 48% / 52% |
| 24.2 | 1% / 0% | 78% / 18% | 47% / 53% |
| 26.4 | 1% / 0% | 79% / 18% | 47% / 53% |
| 28.6 | 1% / 0% | 79% / 18% | 47% / 53% |
| 30.8 | 1% / 0% | 78% / 19% | 50% / 50% |
| 33.0 | 1% / 0% | 79% / 18% | 49% / 51% |
| 35.2 | 1% / 0% | 79% / 18% | 49% / 51% |
| 37.4 | 1% / 0% | 80% / 17% | 45% / 55% |
| 39.6 | 1% / 0% | 79% / 18% | 46% / 54% |
| 41.8 | 1% / 0% | 80% / 17% | 45% / 55% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 16, p95 17, max 18 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Mixed**: busiest reader 79%, workers busy 48% / waiting 52%. Check the timeline for phases.

