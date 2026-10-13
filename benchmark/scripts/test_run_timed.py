# benchmark/scripts/test_run_timed.py
import os, signal, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_timed.py")


def alive(pid):
    """True if pid exists and is not a zombie (in a container without --init, PID 1 never reaps)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:
        with open(f"/proc/{pid}/stat") as fh:
            return fh.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return True


def run(*args):
    out = subprocess.run([sys.executable, RUN, *args], capture_output=True, text=True, check=True).stdout
    return out.strip().split("\t")


class RunTimedTest(unittest.TestCase):
    def test_exit_code_and_wall(self):
        f = run("--", "sh", "-c", "sleep 0.3; exit 3")
        self.assertEqual(len(f), 6)
        self.assertEqual(f[0], "3")
        self.assertGreaterEqual(float(f[1]), 0.3)

    def test_timeout_kills_and_reports_137(self):
        f = run("--timeout", "0.5", "--", "sleep", "5")
        self.assertEqual(f[0], "137")
        self.assertLess(float(f[1]), 3)

    def test_stdout_redirect(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "o.txt")
            run("--stdout", p, "--", "echo", "hi")
            with open(p) as fh:
                self.assertEqual(fh.read().strip(), "hi")

    def test_max_rss_is_positive_kb(self):
        f = run("--", sys.executable, "-c", "x = bytearray(50_000_000); print(len(x))")
        self.assertGreater(int(f[4]), 40_000)  # KB, so > 40 MB

    def test_timeout_kills_whole_process_group(self):
        with tempfile.TemporaryDirectory() as d:
            pidfile = os.path.join(d, "pid")
            f = run("--timeout", "0.5", "--", "sh", "-c", f"sleep 30 & echo $! > {pidfile}; wait")
            self.assertEqual(f[0], "137")
            self.assertLess(float(f[1]), 3)
            with open(pidfile) as fh:
                pid = int(fh.read())
            deadline = time.monotonic() + 1
            while alive(pid):
                self.assertLess(time.monotonic(), deadline, "grandchild survived group kill")
                time.sleep(0.05)

    def assert_signal_kills_child(self, sig):
        with tempfile.TemporaryDirectory() as d:
            pidfile = os.path.join(d, "pid")
            p = subprocess.Popen([sys.executable, RUN, "--timeout", "3600", "--", "sh", "-c",
                                  f"sleep 30 & echo $! > {pidfile}; wait"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + 5
            while not (os.path.exists(pidfile) and os.path.getsize(pidfile)):
                self.assertLess(time.monotonic(), deadline, "child never started")
                time.sleep(0.05)
            with open(pidfile) as fh:
                pid = int(fh.read())
            t0 = time.monotonic()
            os.kill(p.pid, sig)
            try:
                rc = p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
                os.kill(pid, signal.SIGKILL)
                self.fail(f"run_timed.py still running 3 s after signal {sig}")
            self.assertLess(time.monotonic() - t0, 3)
            self.assertNotEqual(rc, 0)
            deadline = time.monotonic() + 1
            while alive(pid):
                if time.monotonic() > deadline:
                    os.kill(pid, signal.SIGKILL)
                    self.fail(f"sleep 30 survived signal {sig} to run_timed.py")
                time.sleep(0.05)

    def test_sigterm_kills_child_group(self):
        self.assert_signal_kills_child(signal.SIGTERM)

    def test_sigint_kills_child_group_and_exits_promptly(self):
        self.assert_signal_kills_child(signal.SIGINT)

    def test_short_run_field6_is_na_or_float(self):
        f = run("--", "true")
        self.assertEqual(len(f), 6)
        if f[5] != "NA":
            float(f[5])

    @unittest.skipUnless(sys.platform.startswith("linux"), "needs /proc")
    def test_thread_cpu_frac_sampled_on_linux(self):
        f = run("--sample-interval", "0.1", "--", sys.executable, "-c",
                "import time; t=time.time()\nwhile time.time()-t<1.5: pass")
        self.assertGreater(float(f[5]), 0.5)


if __name__ == "__main__":
    unittest.main()
