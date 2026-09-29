# fastp trace: /mnt/bench/t.tsv

Processing window (first reader pack to last span): **54.83 s**. Before it (detection sampling on the main thread, and the evaluator's BGZF pool for BGZF input): bgzf_block 0.10 s, bgzf_fetch 0.04 s, worker_wait 0.40 s.

## Time by role (exclusive seconds, summed over the role's threads)

| role | threads | bgzf_block | bgzf_fetch | compress | offset_wait | process | read_pack | reader_wait | worker_wait | write | busy | waiting |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fp-bgzf | 1 | 11.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 21% | 0% |
| fp-read | 1 | 0.0 | 10.3 | 0.0 | 0.0 | 0.0 | 37.8 | 0.0 | 0.0 | 0.0 | 69% | 19% |
| fp-work | 48 | 0.0 | 0.0 | 81.9 | 10.0 | 276.1 | 0.0 | 0.0 | 2260.8 | 1.9 | 14% | 86% |

"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader's work between packs) is counted in neither column.

## Per-read CPU cost

Reads: 42,623,602 over 1 input(s) (42,623,602 per input). "Per read" divides by all reads, so PE pair cost is 2x these.

| stage | where | ns / read | total CPU s | rate |
|---|---|---|---|---|
| BGZF fetch (wait for pool) | reader | 242 | 10.3 | - |
| BGZF block inflate | fp-bgzf pool | 268 | 11.4 | 812 MB/s per thread |
| parse into Read objects | reader | 887 | 37.8 | 245 MB/s per thread |
| trim/filter/stats/serialise | workers | 6477 | 276.1 | - |
| compress (libdeflate) | workers or writer | 1922 | 81.9 | 111 MB/s per thread in, ratio 4.75 |
| write | workers or writer | 45 | 1.9 | - |

Per-read work (trim/filter/stats) is **67%** of traced CPU; the rest is codecs, parsing and I/O.

## Timeline (share of each role's thread-time per bin)

| t (s) | fp-bgzf | fp-read | fp-work |
|---|---|---|---|
| 0.0 | 21% / 0% | 68% / 19% | 13% / 87% |
| 2.7 | 21% / 0% | 69% / 19% | 14% / 86% |
| 5.5 | 22% / 0% | 68% / 20% | 14% / 86% |
| 8.2 | 20% / 0% | 70% / 19% | 13% / 87% |
| 11.0 | 20% / 0% | 69% / 18% | 14% / 85% |
| 13.7 | 22% / 0% | 68% / 20% | 14% / 86% |
| 16.4 | 21% / 0% | 69% / 19% | 13% / 87% |
| 19.2 | 21% / 0% | 69% / 19% | 14% / 86% |
| 21.9 | 20% / 0% | 70% / 18% | 13% / 87% |
| 24.7 | 21% / 0% | 69% / 19% | 14% / 86% |
| 27.4 | 21% / 0% | 69% / 20% | 13% / 86% |
| 30.2 | 21% / 0% | 69% / 19% | 14% / 86% |
| 32.9 | 20% / 0% | 70% / 18% | 14% / 86% |
| 35.6 | 20% / 0% | 70% / 18% | 14% / 86% |
| 38.4 | 20% / 0% | 70% / 18% | 14% / 86% |
| 41.1 | 21% / 0% | 69% / 19% | 14% / 86% |
| 43.9 | 22% / 0% | 69% / 20% | 14% / 86% |
| 46.6 | 20% / 0% | 70% / 18% | 13% / 87% |
| 49.3 | 21% / 0% | 69% / 19% | 13% / 87% |
| 52.1 | 21% / 0% | 67% / 19% | 15% / 85% |

Each cell: busy / waiting.

## Pack backlog (handed to workers, not yet started)

median 48, p95 49, max 51 packs. Near 0 means workers are starved (they wait for the reader); pinned at the backpressure limit means workers or output are the bottleneck.

## Bottleneck

**Mixed**: busiest reader 69%, workers busy 14% / waiting 86%. Check the timeline for phases.

