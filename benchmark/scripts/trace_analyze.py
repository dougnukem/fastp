"""Summarise a fastp trace (`make TRACE=1`, file from $FASTP_TRACE_FILE).

Reports:
  1. per role (fp-read-L, fp-work, fp-bgzf, ...): exclusive seconds in each kind of span and
     how busy the role's threads were over the processing window. Spans nest (compress runs
     inside process), so each span's own time excludes its children.
  2. per-read CPU cost of each stage (ns per read; per pair for PE workers) and codec rates.
     These are the inputs to the reformulation cost model (reformulations.md).
  3. a timeline: per time bin, how busy each role was and how much it waited.
  4. pack backlog: packs handed off by readers but not yet started by workers.
  5. which stage bounds the run.

Usage: trace_analyze.py <trace.tsv> [--bins N] [--json out.json] [--png out.png]
"""
import csv, json, sys
from collections import defaultdict

# bgzf_fetch is the reader waiting on (and copying from) the BGZF pool; the inflate itself is bgzf_block
WAITS = {'reader_wait', 'worker_wait', 'offset_wait', 'bgzf_fetch'}


def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


path = sys.argv[1]
nbins = int(opt('--bins', 20))
json_out, png_out = opt('--json'), opt('--png')

threads = defaultdict(list)
for r in csv.DictReader(open(path), delimiter='\t'):
    threads[r['thread']].append((int(r['t0_ns']), int(r['t1_ns']), r['kind'], int(r['a']), int(r['b'])))
if not threads:
    sys.exit('empty trace')


def role(thread):
    name = thread.split('#')[0]
    if name.startswith('fp-work-'):
        return 'fp-work'
    return name


# exclusive time: a span's duration minus the durations of spans nested directly inside it
excl = defaultdict(lambda: defaultdict(float))       # role -> kind -> seconds
count = defaultdict(lambda: defaultdict(int))         # role -> kind -> spans
sums_a = defaultdict(lambda: defaultdict(int))        # role -> kind -> sum(a)
sums_b = defaultdict(lambda: defaultdict(int))
nthreads = defaultdict(int)
# The main thread ("fastp") reads a sample for adapter/length detection before the pipeline
# starts; keep it out of the processing window and per-read costs, and report it separately.
pipe = {th: evs for th, evs in threads.items() if role(th) != 'fastp'} or threads
t_min = min(e[0] for evs in pipe.values() for e in evs)
t_max = max(e[1] for evs in pipe.values() for e in evs)
flat = []  # (thread, role, t0, t1, kind, exclusive_ns) for the timeline
for th, evs in threads.items():
    ro = role(th)
    nthreads[ro] += 1
    evs.sort(key=lambda e: (e[0], -e[1]))
    stack = []  # [t1, child_ns, index]
    own = [0] * len(evs)
    for i, (t0, t1, kind, a, b) in enumerate(evs):
        while stack and stack[-1][0] <= t0:
            stack.pop()
        if stack:
            own[stack[-1][2]] -= (t1 - t0)
        own[i] += t1 - t0
        stack.append([t1, 0, i])
    for i, (t0, t1, kind, a, b) in enumerate(evs):
        excl[ro][kind] += own[i] / 1e9
        count[ro][kind] += 1
        sums_a[ro][kind] += a
        sums_b[ro][kind] += b
        flat.append((ro, t0, t1, kind, own[i]))

window = (t_max - t_min) / 1e9
main = excl.pop('fastp', {})
nthreads.pop('fastp', None)
flat = [f for f in flat if f[0] != 'fastp']
out = []
p = out.append
p(f'# fastp trace: {path}\n')
p(f'Processing window (first to last pipeline span): **{window:.2f} s**. Before it, the main thread '
  f'spent {sum(main.values()):.2f} s in traced spans (sample reads for detection: '
  + (', '.join(f'{k} {v:.2f} s' for k, v in main.items()) or 'none') + ').\n')

# ---- 1. roles
kinds = sorted({k for ro in excl for k in excl[ro]})
p('## Time by role (exclusive seconds, summed over the role\'s threads)\n')
p('| role | threads | ' + ' | '.join(kinds) + ' | busy | waiting |')
p('|---|---|' + '---|' * len(kinds) + '---|---|')
busy_frac = {}
for ro in sorted(excl):
    cap = nthreads[ro] * window
    work = sum(v for k, v in excl[ro].items() if k not in WAITS)
    wait = sum(v for k, v in excl[ro].items() if k in WAITS)
    busy_frac[ro] = work / cap if cap else 0
    p(f'| {ro} | {nthreads[ro]} | ' + ' | '.join(f'{excl[ro].get(k, 0):.1f}' for k in kinds) +
      f' | {work / cap:.0%} | {wait / cap:.0%} |')
p('\n"busy" is non-wait span time ÷ (threads × window). Time outside any span (e.g. a reader\'s '
  'work between packs) is counted in neither column.\n')

# ---- 2. per-read costs
readers = [ro for ro in excl if ro.startswith('fp-read')]
reads_per_mate = max((sums_a[ro]['read_pack'] for ro in readers), default=0)
reads_total = sum(sums_a[ro]['read_pack'] for ro in readers)
costs = {}


def tot(kind, roles=None):
    return sum(excl[ro].get(kind, 0) for ro in (roles or excl))


def bytes_a(kind):
    return sum(sums_a[ro].get(kind, 0) for ro in excl if ro != 'fastp')


if reads_total:
    ns = lambda s, n: s * 1e9 / n if n else 0
    costs = {
        'reads_total': reads_total,                    # all mates
        'reads_per_mate': reads_per_mate,              # pairs for PE
        'mates': len(readers),
        'decompress_ns_per_read': ns(tot('decompress', readers) + tot('bgzf_block'), reads_total),
        'bgzf_block_ns_per_read': ns(tot('bgzf_block'), reads_total),
        'parse_ns_per_read': ns(tot('read_pack', readers), reads_total),
        'process_ns_per_read': ns(tot('process'), reads_total),
        'compress_ns_per_read': ns(tot('compress'), reads_total),
        'write_ns_per_read': ns(tot('write'), reads_total),
        'uncompressed_in_bytes': bytes_a('decompress') + bytes_a('bgzf_fetch'),
        'compress_in_bytes': bytes_a('compress'),
        'compress_out_bytes': sum(sums_b[ro].get('compress', 0) for ro in excl if ro != 'fastp'),
    }
    p('## Per-read CPU cost\n')
    p(f'Reads: {reads_total:,} over {len(readers)} input(s) ({reads_per_mate:,} per input).'
      ' "Per read" divides by all reads, so PE pair cost is 2x these.\n')
    p('| stage | where | ns / read | total CPU s | rate |')
    p('|---|---|---|---|---|')
    ib = costs['uncompressed_in_bytes']
    dsec = tot('decompress', readers)
    rows = [
        ('decompress (ordinary gzip)', 'reader', ns(dsec, reads_total), dsec,
         f'{bytes_a("decompress") / 1e6 / dsec:.0f} MB/s per thread' if dsec else '-'),
        ('BGZF fetch (wait for pool)', 'reader', ns(tot('bgzf_fetch', readers), reads_total), tot('bgzf_fetch', readers), '-'),
        ('BGZF block inflate', 'fp-bgzf pool', costs['bgzf_block_ns_per_read'], tot('bgzf_block'),
         f'{bytes_a("bgzf_block") / 1e6 / tot("bgzf_block"):.0f} MB/s per thread' if tot('bgzf_block') else '-'),
        ('parse into Read objects', 'reader', costs['parse_ns_per_read'], tot('read_pack', readers),
         f'{ib / 1e6 / tot("read_pack", readers):.0f} MB/s per thread' if tot('read_pack', readers) and ib else '-'),
        ('trim/filter/stats/serialise', 'workers', costs['process_ns_per_read'], tot('process'), '-'),
        ('compress (libdeflate)', 'workers or writer', costs['compress_ns_per_read'], tot('compress'),
         f'{costs["compress_in_bytes"] / 1e6 / tot("compress"):.0f} MB/s per thread in, ratio '
         f'{costs["compress_in_bytes"] / max(costs["compress_out_bytes"], 1):.2f}' if tot('compress') else '-'),
        ('write', 'workers or writer', costs['write_ns_per_read'], tot('write'), '-'),
    ]
    for label, where, n, s, rate in rows:
        if s:
            p(f'| {label} | {where} | {n:.0f} | {s:.1f} | {rate} |')
    cpu_all = sum(v for ro in excl for k, v in excl[ro].items() if k not in WAITS)
    costs['traced_cpu_s'] = cpu_all
    costs['per_read_work_share'] = tot('process') / cpu_all if cpu_all else 0
    p(f'\nPer-read work (trim/filter/stats) is **{costs["per_read_work_share"]:.0%}** of traced CPU; '
      'the rest is codecs, parsing and I/O.\n')

# ---- 3. timeline
p('## Timeline (share of each role\'s thread-time per bin)\n')
bw = (t_max - t_min) / nbins
tl = defaultdict(lambda: defaultdict(float))  # (bin, role) -> 'busy'/'wait' -> ns
for ro, t0, t1, kind, own_ns in flat:
    if own_ns <= 0:
        continue
    # spread a span's own time across the bins it overlaps, proportionally to overlap
    dur = t1 - t0
    b0, b1 = int((t0 - t_min) / bw), min(int((t1 - t_min) / bw), nbins - 1)
    for b in range(b0, b1 + 1):
        lo, hi = max(t0, t_min + b * bw), min(t1, t_min + (b + 1) * bw)
        if hi > lo:
            tl[(b, ro)]['wait' if kind in WAITS else 'busy'] += own_ns * (hi - lo) / dur
roles = sorted(excl)
p('| t (s) | ' + ' | '.join(roles) + ' |')
p('|---|' + '---|' * len(roles))
for b in range(nbins):
    cells = []
    for ro in roles:
        cap = nthreads[ro] * bw
        v = tl[(b, ro)]
        cells.append(f"{v['busy'] / cap:.0%} / {v['wait'] / cap:.0%}")
    p(f'| {b * bw / 1e9:.1f} | ' + ' | '.join(cells) + ' |')
p('\nEach cell: busy / waiting.\n')

# ---- 4. backlog
produced = [e[1] for th, evs in threads.items() if role(th) in readers for e in evs if e[2] == 'read_pack']
started = [e[0] for th, evs in threads.items() if role(th) == 'fp-work' for e in evs if e[2] == 'process']
if produced and started:
    # PE: a worker consumes one pack from each mate, so count backlog in pack pairs
    per = max(len(readers), 1)
    backlog = []
    events = sorted([(t, 1) for t in produced] + [(t, -per) for t in started])
    level = 0
    for t, dlt in events:
        level += dlt
        backlog.append(level / per)
    backlog.sort()
    p('## Pack backlog (handed to workers, not yet started)\n')
    p(f'median {backlog[len(backlog) // 2]:.0f}, p95 {backlog[int(len(backlog) * .95)]:.0f}, '
      f'max {backlog[-1]:.0f} packs. Near 0 means workers are starved (they wait for the reader); '
      'pinned at the backpressure limit means workers or output are the bottleneck.\n')
    costs['backlog_median'] = backlog[len(backlog) // 2]

# ---- 5. verdict
p('## Bottleneck\n')
rb = max((busy_frac[ro] for ro in readers), default=0)
ww = sum(excl['fp-work'].get(k, 0) for k in WAITS) / (nthreads['fp-work'] * window) if nthreads['fp-work'] else 0
wb = busy_frac.get('fp-work', 0)
ow = excl['fp-work'].get('offset_wait', 0) / (nthreads['fp-work'] * window) if nthreads['fp-work'] else 0
if rb >= 0.85 and ww >= 0.15:
    verdict = (f'**Reader-bound**: the busiest reader is {rb:.0%} busy while workers wait {ww:.0%} of the time. '
               'More workers or faster per-read code will not help; faster/parallel decompression and parsing would.')
elif ow >= 0.15:
    verdict = f'**Output-ordering-bound**: workers spend {ow:.0%} waiting for the previous pack\'s output offset.'
elif wb >= 0.8:
    verdict = f'**Worker-bound**: workers are {wb:.0%} busy. Per-read work or compression is the critical path.'
else:
    verdict = (f'**Mixed**: busiest reader {rb:.0%}, workers busy {wb:.0%} / waiting {ww:.0%}. Check the '
               'timeline for phases.')
p(verdict + '\n')
costs.update(reader_busy=rb, worker_busy=wb, worker_wait=ww, window_s=window, verdict=verdict)

text = '\n'.join(out)
print(text)
if json_out:
    json.dump(costs, open(json_out, 'w'), indent=1)
if png_out:
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 1 + 0.4 * len(roles)))
        for y, ro in enumerate(roles):
            for b in range(nbins):
                v = tl[(b, ro)]
                cap = nthreads[ro] * bw
                ax.barh(y, bw / 1e9, left=b * bw / 1e9, color=plt.cm.viridis(min(v['busy'] / cap, 1)))
        ax.set_yticks(range(len(roles)), roles)
        ax.set_xlabel('seconds')
        ax.set_title('busy share per role (yellow = saturated)')
        fig.tight_layout()
        fig.savefig(png_out, dpi=120)
    except ImportError:
        print('(matplotlib not installed; skipped --png)', file=sys.stderr)
