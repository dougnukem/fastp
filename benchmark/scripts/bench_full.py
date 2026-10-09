"""Run one fastp invocation on a full-size input; print a TSV row:
label, result, wall, user, sys, maxrss_kb, pre, detect, process, finalize, reads, bases, digest.
Stages come from stderr timestamps; reads/bases from the JSON report (before filtering).
Usage: bench_full.py <timeout_s> <digest:0|1> <label...tab-joined> -- <fastp args...>
If FASTP_BENCH_THREADS_JSON is set, per-thread CPU (threadcpu.py) is written to that path."""
import json, os, resource, subprocess, sys, threading, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
timeout = float(sys.argv[1]); want_digest = sys.argv[2] == '1'; label = sys.argv[3]
cmd = sys.argv[sys.argv.index('--') + 1:]
t0 = time.time()
p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True, bufsize=1)
timer = threading.Timer(timeout, p.kill); timer.start()
threads_json = os.environ.get('FASTP_BENCH_THREADS_JSON')
sampler = None
if threads_json:
    from threadcpu import Sampler
    sampler = Sampler(p.pid).start()
lines = [(time.time() - t0, l.rstrip('\n')) for l in p.stderr]
rc = p.wait(); timer.cancel(); wall = time.time() - t0
if sampler:
    sampler.stop()
    json.dump(sampler.report(wall), open(threads_json, 'w'))
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
res = 'OK' if rc == 0 else ('HUNG' if rc == -9 else f'EXIT{rc}')
det_idx = [i for i, (_, l) in enumerate(lines) if l.startswith('Detecting adapter')]
stat_idx = next((i for i, (_, l) in enumerate(lines) if l.startswith('Read1 before filtering')), None)
pre = det = proc = fin = float('nan')
if stat_idx is not None:
    t_stats = lines[stat_idx][0]
    if det_idx:
        t_det0 = lines[det_idx[0]][0]
        end = next((i for i in range(det_idx[-1] + 1, stat_idx) if lines[i][1] == ''), stat_idx)
        pre, det, proc = t_det0, lines[end][0] - t_det0, t_stats - lines[end][0]
    else:
        pre, det, proc = 0.0, 0.0, t_stats
    fin = wall - t_stats
reads = bases = 0
digest = '-'
if res == 'OK':
    js = json.load(open(cmd[cmd.index('-j') + 1]))['summary']['before_filtering']
    reads, bases = js['total_reads'], js['total_bases']
    if want_digest:
        outs = ([cmd[cmd.index('-o') + 1]] if '-o' in cmd else []) + ([cmd[cmd.index('-O') + 1]] if '-O' in cmd else [])
        cat = lambda f: 'igzip -dc' if f.endswith('.gz') else 'cat'
        digest = '_'.join(subprocess.run(f"{cat(f)} {f} | md5sum", shell=True, capture_output=True, text=True)
                          .stdout.split()[0][:10] for f in outs) or '-'

print('\t'.join([label, res, f'{wall:.2f}', f'{ru.ru_utime:.2f}', f'{ru.ru_stime:.2f}', str(ru.ru_maxrss),
                 f'{pre:.2f}', f'{det:.2f}', f'{proc:.2f}', f'{fin:.2f}', str(reads), str(bases), digest]), flush=True)
