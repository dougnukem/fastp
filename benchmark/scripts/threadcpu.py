"""Per-thread CPU sampler for a running process (Linux /proc).

Samples /proc/<pid>/task/*/stat about every `interval` seconds and keeps, per thread:
its name (comm), total CPU seconds, first/last time it was seen, and its busiest
1-interval utilisation. fastp names its threads when built from a branch that sets
names (e.g. fp-read-L, fp-work-3); otherwise every thread is "fastp" and the
report falls back to ranking threads by CPU.

A pipeline stage that is the bottleneck shows up as a thread whose CPU seconds are
close to the run's processing time (busy ~100%) while the others have slack.

Used by bench_full.py when FASTP_BENCH_THREADS_JSON is set; also runnable alone:
    python3 threadcpu.py <pid> <out.json> [interval_s]
"""
import json, os, sys, threading, time

TICK = os.sysconf('SC_CLK_TCK')


def _read_threads(pid):
    out = {}
    base = f'/proc/{pid}/task'
    try:
        tids = os.listdir(base)
    except OSError:
        return out
    for tid in tids:
        try:
            with open(f'{base}/{tid}/stat') as f:
                stat = f.read()
            with open(f'{base}/{tid}/comm') as f:
                comm = f.read().strip()
        except OSError:
            continue
        # comm may contain spaces/parens; fields after the last ')' are fixed-position
        rest = stat[stat.rindex(')') + 2:].split()
        utime, stime = int(rest[11]), int(rest[12])
        out[int(tid)] = (comm, (utime + stime) / TICK)
    return out


class Sampler:
    def __init__(self, pid, interval=0.5):
        self.pid, self.interval = pid, interval
        self.threads = {}  # tid -> dict
        self.timeline = []  # (t, {tid: cpu_s})
        self._stop = threading.Event()
        self._t0 = time.time()
        self._th = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._th.start()
        return self

    def _run(self):
        while not self._stop.is_set():
            now = time.time() - self._t0
            snap = _read_threads(self.pid)
            if not snap and self.timeline:
                break
            for tid, (comm, cpu) in snap.items():
                d = self.threads.setdefault(tid, {'comm': comm, 'cpu_s': 0.0, 'first': now,
                                                  'last': now, 'max_util': 0.0, '_prev': (now, cpu)})
                pt, pc = d['_prev']
                if now > pt:
                    d['max_util'] = max(d['max_util'], (cpu - pc) / (now - pt))
                d.update(comm=comm, cpu_s=cpu, last=now, _prev=(now, cpu))
            self.timeline.append((round(now, 2), {t: round(c, 2) for t, (_, c) in snap.items()}))
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()
        self._th.join()

    def report(self, wall=None):
        threads = []
        for tid, d in sorted(self.threads.items(), key=lambda kv: -kv[1]['cpu_s']):
            # a thread seen in k samples lived about k intervals; +interval avoids /0 for short threads
            life = d['last'] - d['first'] + self.interval
            threads.append({'tid': tid, 'comm': d['comm'], 'cpu_s': round(d['cpu_s'], 2),
                            'life_s': round(life, 2), 'busy': round(d['cpu_s'] / life, 3),
                            'max_util': round(min(d['max_util'], 1.5), 3)})
        roles = {}
        for t in threads:
            role = t['comm'].rsplit('-', 1)[0] if t['comm'].startswith('fp-') else t['comm']
            r = roles.setdefault(role, {'threads': 0, 'cpu_s': 0.0, 'max_busy': 0.0})
            r['threads'] += 1
            r['cpu_s'] = round(r['cpu_s'] + t['cpu_s'], 2)
            r['max_busy'] = max(r['max_busy'], t['busy'])
        return {'wall': wall, 'interval': self.interval, 'threads': threads, 'roles': roles,
                'timeline': self.timeline}


if __name__ == '__main__':
    pid, out = int(sys.argv[1]), sys.argv[2]
    s = Sampler(pid, float(sys.argv[3]) if len(sys.argv) > 3 else 0.5).start()
    s._th.join()
    json.dump(s.report(), open(out, 'w'))
