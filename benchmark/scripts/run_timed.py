#!/usr/bin/env python3
"""Run a command and print one TSV line: exit, wall_s, user_s, sys_s, max_rss_kb, max_thread_cpu_frac,
thread_cpu_top.

Usage: run_timed.py [--timeout S] [--stdout FILE] [--stderr FILE] [--sample-interval S] -- CMD...

exit is 137 if --timeout killed the process group. max_thread_cpu_frac is the busiest sampled
thread's CPU seconds divided by wall time (Linux /proc only; NA elsewhere). It is a lower bound:
threads that exit between samples are missed, which is fine for a reader thread that lives
for the whole run. thread_cpu_top is the three busiest sampled threads as tid:comm:frac, busiest
first, comma-separated (NA off Linux). fastp does not name its threads, so comm alone cannot identify
the reader thread.
"""
import argparse
import os
import signal
import subprocess
import sys
import threading
import time


def thread_cpu(pid):
    """{tid: cpu_seconds} from /proc (Linux). Empty dict if unavailable."""
    out = {}
    try:
        tck = os.sysconf("SC_CLK_TCK")
        for tid in os.listdir(f"/proc/{pid}/task"):
            with open(f"/proc/{pid}/task/{tid}/stat") as f:
                s = f.read()
            fields = s[s.rindex(")") + 2:].split()  # fields[0] is stat field 3 (state)
            out[tid] = (int(fields[11]) + int(fields[12])) / tck  # utime + stime
    except (OSError, ValueError):
        pass
    return out


def thread_comm(pid, tid):
    """Thread name from /proc, with the TSV and list separators replaced."""
    try:
        with open(f"/proc/{pid}/task/{tid}/comm") as f:
            name = f.read().strip()
    except OSError:
        return "NA"
    return "".join("_" if c in "\t,: " else c for c in name) or "NA"


def main():
    argv = sys.argv[1:]
    i = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=0)
    ap.add_argument("--stdout", default=os.devnull)
    ap.add_argument("--stderr", default=os.devnull)
    ap.add_argument("--sample-interval", type=float, default=0.5)
    args, cmd = ap.parse_args(argv[:i]), argv[i + 1:]

    def stop(sig, _frame):
        raise SystemExit(128 + sig)  # unwinds through the wait below, which kills the child group

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    with open(args.stdout, "wb") as so, open(args.stderr, "wb") as se:
        t0 = time.monotonic()
        p = subprocess.Popen(cmd, stdout=so, stderr=se, start_new_session=True)
        done = threading.Event()
        peak, comm = {}, {}

        def sampler():
            while not done.wait(args.sample_interval):
                for tid, c in thread_cpu(p.pid).items():
                    peak[tid] = max(peak.get(tid, 0.0), c)
                    if tid not in comm:
                        comm[tid] = thread_comm(p.pid, tid)

        def kill():
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        try:  # from here on, any exit (including SIGINT/SIGTERM via stop) must take the child with it
            st = threading.Thread(target=sampler, daemon=True)
            st.start()
            timer = threading.Timer(args.timeout, kill) if args.timeout else None
            if timer:
                timer.daemon = True  # never keep Python alive after an interrupt
                timer.start()
            _, status, ru = os.wait4(p.pid, 0)
        except BaseException:
            kill()  # the child has its own session, so nothing else would stop it
            raise
        wall = time.monotonic() - t0
        done.set()
        st.join(timeout=2)
        if timer:
            timer.cancel()

    code = os.waitstatus_to_exitcode(status)
    if code < 0:
        code = 128 - code
    p.returncode = code
    rss_kb = ru.ru_maxrss // 1024 if sys.platform == "darwin" else ru.ru_maxrss
    frac, top = "NA", "NA"
    if peak and wall > 0:
        busiest = sorted(peak, key=peak.get, reverse=True)
        frac = f"{peak[busiest[0]] / wall:.3f}"
        top = ",".join(f"{t}:{comm[t]}:{peak[t] / wall:.3f}" for t in busiest[:3])
    print(f"{code}\t{wall:.3f}\t{ru.ru_utime:.3f}\t{ru.ru_stime:.3f}\t{rss_kb}\t{frac}\t{top}")


if __name__ == "__main__":
    main()
