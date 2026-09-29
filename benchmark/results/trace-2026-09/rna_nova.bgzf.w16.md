# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **55.91 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.31 s, bgzf_fetch 0.09 s, worker_wait 0.20 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 28 | 35.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2% | 0% |
| fp-read-L | 1 | 0.0 | 5.1 | 0.0 | 0.0 | 0.0 | 26.8 | 23.6 | 0.0 | 0.0 | 48% | 51% |
| fp-read-R | 1 | 0.0 | 5.0 | 0.0 | 0.0 | 0.0 | 26.1 | 24.3 | 0.0 | 0.0 | 47% | 52% |
| fp-work | 16 | 0.0 | 0.0 | 178.4 | 29.6 | 625.9 | 0.0 | 0.0 | 57.5 | 3.0 | 90% | 10% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 62,078,114 over 2 input(s) (31,039,057 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 162 | 10.1 | - |
| BGZF block inflate | fp-bgzf pool | 567 | 35.2 | 592 MB/s per thread |
| parse into Read objects | reader | 853 | 53.0 | 394 MB/s per thread |
| trim/filter/stats/serialise | workers | 10082 | 625.9 | - |
| compress (libdeflate) | workers or writer | 2873 | 178.4 | 116 MB/s per thread in, ratio 4.87 |
| write | workers or writer | 49 | 3.0 | - |

Per-read work (trim/filter/stats) is **70%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read-L | fp-read-R | fp-work |
|---|---|---|---|---|
| 0.0 | 2% / 0% | 35% / 64% | 34% / 65% | 78% / 22% |
| 2.8 | 2% / 0% | 39% / 60% | 39% / 60% | 81% / 19% |
| 5.6 | 2% / 0% | 43% / 56% | 42% / 57% | 86% / 14% |
| 8.4 | 2% / 0% | 48% / 52% | 45% / 54% | 90% / 10% |
| 11.2 | 2% / 0% | 46% / 54% | 49% / 51% | 94% / 6% |
| 14.0 | 2% / 0% | 46% / 53% | 46% / 53% | 89% / 11% |
| 16.8 | 2% / 0% | 50% / 50% | 50% / 49% | 90% / 10% |
| 19.6 | 2% / 0% | 52% / 47% | 53% / 46% | 92% / 8% |
| 22.4 | 2% / 0% | 51% / 48% | 46% / 54% | 89% / 11% |
| 25.2 | 2% / 0% | 48% / 52% | 49% / 50% | 94% / 7% |
| 28.0 | 2% / 0% | 49% / 50% | 51% / 48% | 96% / 5% |
| 30.7 | 2% / 0% | 50% / 50% | 47% / 52% | 88% / 12% |
| 33.5 | 2% / 0% | 47% / 52% | 49% / 50% | 89% / 11% |
| 36.3 | 2% / 0% | 50% / 50% | 47% / 53% | 89% / 11% |
| 39.1 | 2% / 0% | 53% / 46% | 48% / 52% | 90% / 10% |
| 41.9 | 2% / 0% | 53% / 46% | 47% / 52% | 95% / 5% |
| 44.7 | 2% / 0% | 51% / 49% | 50% / 50% | 96% / 4% |
| 47.5 | 2% / 0% | 52% / 47% | 49% / 50% | 91% / 9% |
| 50.3 | 3% / 0% | 50% / 50% | 49% / 50% | 96% / 4% |
| 53.1 | 2% / 0% | 47% / 51% | 45% / 53% | 91% / 9% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 16, p95 18, max 24 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Worker-bound**: workers are 90% busy. Per-read work or compression is the critical path.

