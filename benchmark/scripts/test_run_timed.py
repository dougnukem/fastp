# benchmark/scripts/test_run_timed.py
import os, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_timed.py")


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
            while True:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                self.assertLess(time.monotonic(), deadline, "grandchild survived group kill")
                time.sleep(0.05)

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
