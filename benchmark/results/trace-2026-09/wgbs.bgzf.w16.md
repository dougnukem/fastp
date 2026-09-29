# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **40.23 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.25 s, bgzf_fetch 0.07 s, worker_wait 0.14 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 28 | 27.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2% | 0% |
| fp-read-L | 1 | 0.0 | 3.2 | 0.0 | 0.0 | 0.0 | 23.5 | 13.0 | 0.0 | 0.0 | 58% | 40% |
| fp-read-R | 1 | 0.0 | 6.0 | 0.0 | 0.0 | 0.0 | 27.4 | 6.3 | 0.0 | 0.0 | 68% | 31% |
| fp-work | 16 | 0.0 | 0.0 | 168.4 | 22.3 | 351.3 | 0.0 | 0.0 | 98.5 | 2.9 | 81% | 19% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 56,760,748 over 2 input(s) (28,380,374 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 162 | 9.2 | - |
| BGZF block inflate | fp-bgzf pool | 476 | 27.0 | 732 MB/s per thread |
| parse into Read objects | reader | 897 | 50.9 | 389 MB/s per thread |
| trim/filter/stats/serialise | workers | 6190 | 351.3 | - |
| compress (libdeflate) | workers or writer | 2966 | 168.4 | 117 MB/s per thread in, ratio 5.17 |
| write | workers or writer | 51 | 2.9 | - |

Per-read work (trim/filter/stats) is **59%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|---|
| 0.0 | 2% / 0% | 47% / 51% | 57% / 41% | 75% / 25% |
| 2.0 | 2% / 0% | 52% / 47% | 61% / 38% | 78% / 21% |
| 4.0 | 2% / 0% | 58% / 41% | 68% / 31% | 81% / 19% |
| 6.0 | 2% / 0% | 58% / 41% | 68% / 31% | 81% / 19% |
| 8.0 | 2% / 0% | 57% / 41% | 66% / 32% | 81% / 19% |
| 10.1 | 2% / 0% | 58% / 41% | 67% / 31% | 83% / 17% |
| 12.1 | 2% / 0% | 59% / 40% | 63% / 35% | 79% / 21% |
| 14.1 | 2% / 0% | 60% / 39% | 66% / 33% | 80% / 20% |
| 16.1 | 2% / 0% | 60% / 39% | 70% / 29% | 82% / 18% |
| 18.1 | 2% / 0% | 58% / 41% | 67% / 31% | 82% / 18% |
| 20.1 | 2% / 0% | 65% / 34% | 70% / 29% | 82% / 18% |
| 22.1 | 2% / 0% | 62% / 37% | 69% / 30% | 83% / 17% |
| 24.1 | 2% / 0% | 59% / 40% | 70% / 29% | 83% / 17% |
| 26.1 | 3% / 0% | 59% / 40% | 74% / 25% | 84% / 16% |
| 28.2 | 2% / 0% | 64% / 35% | 73% / 26% | 83% / 17% |
| 30.2 | 2% / 0% | 62% / 37% | 70% / 29% | 81% / 19% |
| 32.2 | 3% / 0% | 65% / 34% | 72% / 27% | 81% / 19% |
| 34.2 | 2% / 0% | 54% / 45% | 69% / 30% | 79% / 20% |
| 36.2 | 2% / 0% | 55% / 44% | 72% / 27% | 81% / 19% |
| 38.2 | 3% / 0% | 57% / 40% | 71% / 26% | 84% / 15% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 17, p95 19, max 24 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Worker-bound**: workers are 81% busy. Per-read work or compression is the critical path.

