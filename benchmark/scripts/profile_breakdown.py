#!/usr/bin/env python3
"""Turn profile_run.sh output into a per-code-path cost model.

For each profile directory: CPU seconds per code path (from on-CPU stacks),
CPU-microseconds per read (or pair), how many threads were saturated, and the
throughput ceiling each resource implies. Rerun it on a new build's profiles
to see which costs changed; RULES maps stack frames to code paths and is the
part to update if functions are renamed.

usage: profile_breakdown.py <reads> <workers> <fixed_s> PROFILE_DIR [PROFILE_DIR ...]
  reads    reads (or pairs for PE) in the profiled input
  workers  the -w used
  fixed_s  seconds in fixed stages (pre + detect + report) for this input, from a
           timed run; throughput is computed over the processing stage only
"""
import collections, re, sys

RULES = [  # (code path, frame substrings); a sample goes to the leaf-most matching frame
    ('adapter trim (per read)', ['Matcher::', 'AdapterTrimmer::']),
    ('overlap/merge', ['OverlapAnalysis']),
    ('dedup', ['Duplicate::']),
    ('stats/QC', ['Stats::', 'FilterResult', 'Evaluator::computeOverRep']),
    ('filter/quality trim/polyX', ['Filter::', 'Trimmer::', 'PolyX', 'UmiProcessor', 'BaseCorrector']),
    ('adapter detection', ['Evaluator::']),
    ('output compression', ['libdeflate', 'deflate', 'isal_deflate', 'Writer', 'WriterThread']),
    ('input decompression', ['decode_huffman', 'isal_inflate', 'crc32_gzip', 'inflate', 'gzread']),
    ('FASTQ parse', ['FastqReader', 'Read::Read', 'ReadPool']),
    ('queue/sync (waiting)', ['canBeConsumed', 'SingleProducerSingleConsumer', 'PackRing', 'futex',
                              'pthread_cond', 'usleep', 'nanosleep', 'sched_yield', 'atomic']),
]


def classify(stack):
    for frame in reversed(stack.split(';')):
        for path, keys in RULES:
            if any(k in frame for k in keys):
                return path
    return 'other (libc, allocation, strings)'


def threads(path):
    """Mean %CPU per thread over the middle 80% of the run (skips startup and report)."""
    cpu = collections.defaultdict(list)
    for line in open(path):
        p = line.split()
        if len(p) == 11 and p[-1].startswith('|__') and p[3] != '-':
            cpu[p[3]].append(float(p[8]))
    out = []
    for v in cpu.values():
        if len(v) >= 20:
            k = len(v) // 10
            v = v[k:len(v) - k]
            out.append(sum(v) / len(v))
    return sorted(out, reverse=True)


def main():
    reads, workers, fixed_s, dirs = float(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3]), sys.argv[4:]
    for d in dirs:
        samples, total = collections.Counter(), 0
        for line in open(f'{d}/folded.txt'):
            stack, n = line.rsplit(' ', 1)
            samples[classify(stack)] += int(n)
            total += int(n)
        stat = open(f'{d}/stat.txt').read()
        task, elapsed = re.search(r'([\d.]+) msec task-clock', stat), re.search(r'([\d.]+) seconds time elapsed', stat)
        if not task or not elapsed:
            sys.exit(f"{d}/stat.txt: no task-clock/elapsed lines")
        cpu_s, wall = float(task.group(1)) / 1000, float(elapsed.group(1))
        th = threads(f'{d}/threads.txt')
        pinned = sum(1 for x in th if x >= 90)
        us_per_read = 1e6 * cpu_s / reads
        waiting = samples['queue/sync (waiting)'] / total
        work_us = us_per_read * (1 - waiting)
        print(f"\n## {d}")
        print(f"wall {wall:.1f}s, CPU {cpu_s:.0f}s ({cpu_s / wall:.1f} CPUs busy), {us_per_read:.1f} CPU-us per read")
        print(f"threads: {len(th)}, saturated (>=90%): {pinned}, top: {' '.join(f'{x:.0f}' for x in th[:4])}, "
              f"median {th[len(th) // 2]:.0f}%" if th else "threads: no pidstat data")
        print(f"measured processing throughput {reads / (wall - fixed_s) / 1e6:.2f}M/s (profiled run, includes perf overhead); worker ceiling if CPU-bound "
              f"{workers / work_us:.2f}M/s ({workers} workers / {work_us:.1f} us of non-waiting work per read)")
        print("| code path | share | CPU-s | CPU-us per read |\n|---|---|---|---|")
        for path, n in samples.most_common():
            print(f"| {path} | {100 * n / total:.1f}% | {cpu_s * n / total:.0f} | {us_per_read * n / total:.2f} |")


if __name__ == '__main__':
    main()
