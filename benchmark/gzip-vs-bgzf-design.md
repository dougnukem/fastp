# Design: how much of a fastp run is serial gzip decode, and what does BGZF buy?

Status: draft for review. No fastp source changes in this PR.

## Question

fastp decodes plain `.fastq.gz` on one thread per input file (ISA-L, `FastqReader::readToBufIgzip`).
BGZF input already takes a multithreaded path (`BgzfMtReader`, upstream v1.4.0), with a thread budget
derived from `--thread` in `peprocessor.cpp` / `seprocessor.cpp`. Nobody has published how much
wall time the serial plain-gzip decode costs, or what BGZF input actually saves end to end.

We need that number before proposing any new reader (for example parallel decode of plain gzip).

## Goals

1. For medium (1-5 GB `.gz` per file) and large (about 10 GB `.gz` per file) FASTQ, report fastp wall time
   for the same reads as plain gzip and as BGZF, at `-w` 1/2/4/8/16 (32 on the 48-vCPU box).
2. Show whether the plain-gzip reader thread is saturated (decode-bound) at each `-w`.
3. Compare measured wall time with the standalone single-thread decode floor, to give an Amdahl-style ceiling.
4. Verify both formats produce identical output (order-independent digest, as in `run_backfill.sh`).

## Non-goals

- No change to fastp behavior, flags or defaults.
- No plain-gzip parallel reader, no zstd/CRAM/ORA input. Those are follow-ups, gated on these numbers.
- No Form Bio production data, paths or usage details. Public accessions only.

## Method

**Inputs.** Reuse the corpus in [corpus.md](corpus.md). `wgs` (SRR952827) is the medium case. The large case is
the same accession truncated at more read pairs, not replicated data, so compression behavior stays realistic.
`fetch_corpus.sh` re-compresses with `gzip -1`, which decodes faster than real instrument output, so neither variant
is taken from it directly. Both variants are rebuilt from the same decompressed reads at the same level (default 6):
plain with `gzip -6`, BGZF with `bgzip -l 6`. File size then differs only by BGZF block overhead. Record both sizes and
the level.

**Modes** (each at every thread count, 3 runs, median):

| mode | fastp flags | isolates |
|---|---|---|
| A decode-heavy | all trimming and filtering disabled, no output files, JSON to `/dev/null` | reader + minimal work |
| B default, no output | defaults, no `-o` | reader + full per-read work |
| C default, gz output | defaults, `-o/-O *.gz` | whole pipeline including parallel output compression |

**Decode baselines** (no fastp): `gzip -dc`, `igzip -dc` (if available), `bgzip -dc -@ N`, and `rapidgzip -P N`
(if available), each piped to `/dev/null`. The decode floor is `igzip`'s single-thread time on the plain file, because
fastp decodes plain gzip with ISA-L; `gzip -dc` is reported for information only, and without `igzip` the verdict is
inconclusive. Per-thread CPU is sampled
during the fastp runs (`pidstat -t` or `top -H`), and thread names come from the existing pack-trace work (#11),
so the claim "reader thread at ~100% CPU" is observed, not inferred.

**Hardware.** Numbers that go in the PR come from the same 48-vCPU AMD EPYC (n2d-highmem-48) used for the
backfill, with data on local SSD and the page cache warmed (or dropped, recorded per run). Laptop runs are
smoke tests only.

**Outputs.** `benchmark/scripts/bench_gzip_vs_bgzf.sh` writes `benchmark/results/gzip-vs-bgzf-<date>.tsv`
(columns: dataset, format, mode, threads, run, wall_s, user_s, sys_s, max_rss_kb, output_digest) and
`analyze.py` gains a summary table: BGZF/plain speedup per `-w`, plain-gzip wall vs decode floor, and a
digest-mismatch flag.

## Decision rule for the follow-up (proposed, for review)

Evaluated on mode C (the realistic pipeline) at `-w 16`. The decode floor is the single-thread `igzip` decode time of the
slower mate, because paired-end runs give each mate its own reader thread. Propose a plain-gzip parallel reader
upstream only if, on the large file, both hold:

- plain-gzip wall time is within about 30% of the single-thread decode floor (decode-bound), and
- BGZF input is at least 1.5x faster end to end.

Otherwise the recommendation is to document "BGZF-ize on ingest" and stop.

## Risks

- The page cache can hide or exaggerate I/O cost. Record the cache state per run.
- A large file is only meaningful if it exceeds what one decode thread can feed in a few seconds. Large is about 10 GB `.gz` for that reason.
- `igzip` and `rapidgzip` may not be installed. Missing baselines are reported as absent, not estimated.
- The BGZF budget formula is `max(1, (cpus - (workers + 4)) / gz inputs)`, and gz inputs are counted by a `.gz` file extension. At high `-w` on a small box it can drop to 1, which would make BGZF look no better than plain gzip. Record the effective budget.
