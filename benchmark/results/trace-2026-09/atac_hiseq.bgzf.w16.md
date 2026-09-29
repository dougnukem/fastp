# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **185.40 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.22 s, bgzf_fetch 0.05 s, worker_wait 0.14 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 28 | 109.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2% | 0% |
| fp-read-L | 1 | 0.0 | 14.2 | 0.0 | 0.0 | 0.0 | 150.8 | 16.9 | 0.0 | 0.0 | 81% | 17% |
| fp-read-R | 1 | 0.0 | 14.1 | 0.0 | 0.0 | 0.0 | 149.6 | 18.2 | 0.0 | 0.0 | 81% | 17% |
| fp-work | 16 | 0.0 | 0.0 | 642.1 | 68.8 | 1624.0 | 0.0 | 0.0 | 615.7 | 15.1 | 77% | 23% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 385,809,298 over 2 input(s) (192,904,649 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 73 | 28.3 | - |
| BGZF block inflate | fp-bgzf pool | 284 | 109.5 | 595 MB/s per thread |
| parse into Read objects | reader | 779 | 300.4 | 217 MB/s per thread |
| trim/filter/stats/serialise | workers | 4209 | 1624.0 | - |
| compress (libdeflate) | workers or writer | 1664 | 642.1 | 98 MB/s per thread in, ratio 3.64 |
| write | workers or writer | 39 | 15.1 | - |

Per-read work (trim/filter/stats) is **60%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|---|
| 0.0 | 2% / 0% | 74% / 25% | 72% / 27% | 76% / 24% |
| 9.3 | 2% / 0% | 84% / 14% | 79% / 19% | 75% / 25% |
| 18.5 | 2% / 0% | 84% / 14% | 75% / 23% | 79% / 21% |
| 27.8 | 2% / 0% | 74% / 24% | 86% / 12% | 77% / 23% |
| 37.1 | 2% / 0% | 76% / 22% | 87% / 11% | 77% / 23% |
| 46.4 | 2% / 0% | 78% / 20% | 87% / 11% | 77% / 23% |
| 55.6 | 2% / 0% | 85% / 13% | 74% / 24% | 77% / 23% |
| 64.9 | 2% / 0% | 86% / 12% | 81% / 17% | 73% / 27% |
| 74.2 | 2% / 0% | 78% / 20% | 86% / 12% | 77% / 23% |
| 83.4 | 2% / 0% | 77% / 21% | 84% / 14% | 77% / 23% |
| 92.7 | 2% / 0% | 83% / 15% | 82% / 17% | 81% / 19% |
| 102.0 | 2% / 0% | 84% / 14% | 80% / 19% | 80% / 20% |
| 111.2 | 2% / 0% | 85% / 13% | 77% / 21% | 78% / 22% |
| 120.5 | 2% / 0% | 81% / 17% | 79% / 19% | 76% / 24% |
| 129.8 | 2% / 0% | 80% / 18% | 84% / 14% | 76% / 24% |
| 139.1 | 2% / 0% | 86% / 12% | 80% / 18% | 77% / 22% |
| 148.3 | 2% / 0% | 87% / 11% | 76% / 22% | 76% / 24% |
| 157.6 | 2% / 0% | 84% / 14% | 87% / 11% | 74% / 26% |
| 166.9 | 2% / 0% | 81% / 17% | 79% / 19% | 75% / 25% |
| 176.1 | 2% / 0% | 80% / 18% | 80% / 18% | 79% / 21% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 17, p95 19, max 25 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Mixed**: busiest reader 81%, workers busy 77% / waiting 23%. Check the timeline for phases.

