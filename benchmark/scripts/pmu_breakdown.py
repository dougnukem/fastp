#!/usr/bin/env python3
"""Summarise profile_pmu.sh output: top-down breakdown per run, then per-function
share of cycles / instructions / branch misses with IPC and branch misses per 1k instructions.

usage: pmu_breakdown.py PROFILE_DIR [PROFILE_DIR ...]
Symbol names are matched across the three sampled events after dropping arguments,
because perf truncates names to a per-section column width.
"""
import collections, csv, os, re, sys


def counters(path):
    out = {}
    for row in csv.reader(l for l in open(path) if l.strip() and not l.startswith('#')):
        if len(row) > 2 and row[0].replace('.', '').isdigit():
            out[row[2]] = float(row[0])
    return out


def functions(path):
    event, table = None, collections.defaultdict(lambda: collections.defaultdict(float))
    for line in open(path):
        m = re.match(r"# Samples: .* of event '([a-z-]+)", line)
        if m:
            event = m.group(1)
            continue
        # perf pads names to the widest symbol, so drop the padding and the trailing "- -" columns
        # before matching; a lazy regex on the padded line is quadratic and effectively hangs
        line = re.sub(r'\s+-\s+-$', '', line.rstrip())
        m = re.match(r"\s*([\d.]+)%\s+\[.\]\s+(.*)$", line)
        if m and event:
            table[event][re.sub(r'\(.*', '', m.group(2)).strip()] += float(m.group(1))
    return table


def main():
    dirs = sys.argv[1:]
    print(f"{'run':16s} {'retiring':>8s} {'bad-spec':>8s} {'fe-bound':>8s} {'be-bound':>8s} | {'br-mispred':>10s} {'fetch-lat':>9s} {'fe-bw':>6s} {'mem-bound':>9s} {'core-bound':>10s} | {'IPC':>5s} {'br-miss%':>8s}")
    totals = {}
    for d in dirs:
        t, m = counters(f'{d}/topdown.csv'), counters(f'{d}/totals.csv')
        totals[d] = m
        four = sum(t[k] for k in ('topdown-retiring', 'topdown-bad-spec', 'topdown-fe-bound', 'topdown-be-bound'))
        pct = lambda k: 100 * t[k] / four
        fe, be = pct('topdown-fe-bound'), pct('topdown-be-bound')
        print(f"{os.path.basename(d.rstrip('/')):16s} {pct('topdown-retiring'):8.1f} {pct('topdown-bad-spec'):8.1f} {fe:8.1f} {be:8.1f} | "
              f"{pct('topdown-br-mispredict'):10.1f} {pct('topdown-fetch-lat'):9.1f} {fe - pct('topdown-fetch-lat'):6.1f} "
              f"{pct('topdown-mem-bound'):9.1f} {be - pct('topdown-mem-bound'):10.1f} | "
              f"{m['instructions'] / m['cycles']:5.2f} {100 * m['branch-misses'] / m['branches']:8.2f}")
    for d in dirs:
        f, m = functions(f'{d}/report.txt'), totals[d]
        print(f"\n{os.path.basename(d.rstrip('/'))}: % of cycles / instructions / branch-misses, IPC, branch-misses per 1k instructions")
        for fn, cy in sorted(f['cycles'].items(), key=lambda x: -x[1])[:10]:
            i, b = f['instructions'].get(fn, 0), f['branch-misses'].get(fn, 0)
            if i == 0 or fn.startswith('0x'):
                continue  # unresolved address: keys differ between sections
            ipc = i * m['instructions'] / (cy * m['cycles'])
            mpki = b * m['branch-misses'] / (i * m['instructions'] / 1000)
            print(f"  {cy:5.1f}% {i:5.1f}% {b:5.1f}%  IPC {ipc:4.2f}  MPKI {mpki:5.1f}  {fn[:70]}")


if __name__ == '__main__':
    main()
