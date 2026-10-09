"""Turn io_variants.sh (+ optional codec_baselines.sh) results into a per-stage breakdown.

For each (dataset, threads), medians over reps, it reports:

  wall and CPU-seconds of every variant, and these differences against gz_gz:
    input decompression   gz_gz - plain_gz     (wall saved / CPU saved by not inflating)
    output compression    gz_gz - gz_plain
    output write          gz_plain - gz_none
    compute floor         plain_none           (parse + trim/filter + stats, no codecs)
    BGZF input            gz_gz - bgzf_gz      (what fastp's parallel BGZF reader recovers)

  the reader ceiling: uncompressed bytes of the larger mate / single-thread igzip MB/s.
  If gz_gz processing time is close to it and the busiest thread is ~100% busy, the run
  is bound by single-threaded decompression, and adding workers (or a GPU) cannot help.

  the busiest threads (threadcpu.py JSON), by role when fastp names its threads.

Wall differences are not additive: stages overlap across threads, so removing one only
saves wall time if it was on the critical path. CPU-second differences are additive and
are what matters for cost (CPU-hours), wall differences for turnaround.

Also flags any variant whose output digest differs from the others for the same cell
(outputs must not depend on the I/O mode).

Usage: decompose.py <io_variants.tsv> [codec_baselines.tsv] [--prep <work_dir>/prep.tsv] [--md out.md]
"""
import csv, json, os, statistics, sys
from collections import defaultdict

def opt(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


md_out, prep = opt('--md'), opt('--prep')
args = [a for a in sys.argv[1:] if not a.startswith('--') and a not in (md_out, prep)]
io_tsv = args[0]
codec_tsv = args[1] if len(args) > 1 else None

rows = [r for r in csv.DictReader(open(io_tsv), delimiter='\t') if r['result'] == 'OK']
cells = defaultdict(lambda: defaultdict(list))
digests = defaultdict(dict)
for r in rows:
    k = (r['dataset'], r['threads'])
    cells[k][r['variant']].append(r)
    if r['digest'] not in ('-', ''):
        digests[k][r['variant']] = r['digest']

igzip_mbps, plain_bytes = {}, {}
codec_lines = []
if codec_tsv and os.path.exists(codec_tsv):
    for c in csv.DictReader(open(codec_tsv), delimiter='\t'):
        if c['tool'] == 'igzip' and c['op'] == 'decompress':
            igzip_mbps[c['dataset']] = float(c['uncomp_MBps'])
        codec_lines.append(c)

if prep and os.path.exists(prep):
    for p in csv.DictReader(open(prep), delimiter='\t'):
        if 'gunzip' in p['step']:
            ds, mate = p['step'].split('.')[:2]
            plain_bytes[(ds, mate)] = int(p['out_bytes'])


def med(rs, f):
    return statistics.median(float(r[f]) for r in rs)


def cpu(rs):
    return statistics.median(float(r['user']) + float(r['sys']) for r in rs)


out = []
p = out.append
p('# Codec / I/O decomposition\n')
p(f'Source: `{os.path.basename(io_tsv)}`' + (f', `{os.path.basename(codec_tsv)}`' if codec_tsv else '') + '\n')
ORDER = ['gz_gz', 'gz_gz_z1', 'gz_plain', 'gz_none', 'plain_gz', 'plain_plain', 'plain_none', 'bgzf_gz', 'bgzf_plain']
for (ds, t), vs in sorted(cells.items()):
    p(f'\n## {ds}, -w {t}\n')
    p('| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |')
    p('|---|---|---|---|---|---|---|')
    for v in [v for v in ORDER if v in vs] + [v for v in vs if v not in ORDER]:
        rs = vs[v]
        w, pr, c = med(rs, 'wall'), med(rs, 'process'), cpu(rs)
        reads = int(rs[0]['reads'])
        tj = os.path.join(io_tsv + '.threads', f'{ds}.{v}.{t}.{rs[0]["rep"]}.json')
        busiest = '-'
        if os.path.exists(tj):
            th = json.load(open(tj))['threads'][:3]
            busiest = ', '.join(f"{x['comm']}: {x['busy']:.0%}" for x in th)
        p(f'| {v} | {w:.1f} | {pr:.1f} | {c:.0f} | {c / w:.1f} | {reads / pr / 1e6:.2f} | {busiest} |')

    def d(a, b, f):
        if a in vs and b in vs:
            return (med(vs[a], f) - med(vs[b], f)) if f != 'cpu' else (cpu(vs[a]) - cpu(vs[b]))
        return None
    p('\n| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |')
    p('|---|---|---|---|')
    base_cpu = cpu(vs['gz_gz']) if 'gz_gz' in vs else None
    for label, a, b in [('input decompression (gz_gz − plain_gz)', 'gz_gz', 'plain_gz'),
                        ('output compression (gz_gz − gz_plain)', 'gz_gz', 'gz_plain'),
                        ('output write (gz_plain − gz_none)', 'gz_plain', 'gz_none'),
                        ('both codecs (gz_gz − plain_plain)', 'gz_gz', 'plain_plain'),
                        ('BGZF input (gz_gz − bgzf_gz)', 'gz_gz', 'bgzf_gz'),
                        ('-z 4 → -z 1 (gz_gz − gz_gz_z1)', 'gz_gz', 'gz_gz_z1')]:
        dw, dc = d(a, b, 'wall'), d(a, b, 'cpu')
        if dw is None or dc is None:
            continue
        share = f'{dc / base_cpu:.0%}' if base_cpu else '-'
        p(f'| {label} | {dw:.1f} | {dc:.0f} | {share} |')
    if 'plain_none' in vs and base_cpu:
        p(f'| compute floor: plain_none CPU | – | {cpu(vs["plain_none"]):.0f} | '
          f'{cpu(vs["plain_none"]) / base_cpu:.0%} |')
    mates = [b for (dd, _), b in plain_bytes.items() if dd == ds]
    if ds in igzip_mbps and mates and 'gz_gz' in vs:
        ceil = max(mates) / 1e6 / igzip_mbps[ds]
        pr = med(vs['gz_gz'], 'process')
        p(f'\nReader ceiling (largest mate {max(mates) / 1e9:.1f} GB ÷ igzip {igzip_mbps[ds]:.0f} MB/s, one thread): '
          f'**{ceil:.1f} s** vs gz_gz processing {pr:.1f} s → {ceil / pr:.0%} of processing time is the '
          f'minimum a single-threaded inflate needs.')
    ds_dig = digests[(ds, t)]
    outputs = {v: g for v, g in ds_dig.items() if not v.endswith('_none')}
    if len(set(outputs.values())) > 1:
        p(f'\n**Output digests differ across variants:** {outputs}')

if codec_lines:
    p('\n## Standalone codec throughput (page cache → /dev/null)\n')
    p('| dataset | tool | op | threads | level | wall s | MB/s (uncompressed) | MB/s per CPU-core |')
    p('|---|---|---|---|---|---|---|---|')
    for c in codec_lines:
        p(f"| {c['dataset']} | {c['tool']} | {c['op']} | {c['threads']} | {c['level']} | {c['wall']} | "
          f"{c['uncomp_MBps']} | {c['cpu_MBps_per_core']} |")

text = '\n'.join(out) + '\n'
if md_out:
    open(md_out, 'w').write(text)
print(text)
