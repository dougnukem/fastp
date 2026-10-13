# benchmark/scripts/test_analyze_gzip_vs_bgzf.py
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_gzip_vs_bgzf as a


def bench_row(fmt, wall, t=16, mode="C", reads="100", digest="-", ds="big", result="OK"):
    return dict(dataset=ds, format=fmt, mode=mode, threads=str(t), result=result, wall_s=str(wall),
                max_thread_cpu_frac="0.99", reads_after=reads, digest=digest)


def base_row(mate, wall, variant="plain", tool="gzip", t="1", result="OK", ds="big"):
    return dict(dataset=ds, mate=mate, variant=variant, tool=tool, threads=t, result=result,
                wall_s=str(wall), uncompressed_bytes="1")


class AnalyzeTest(unittest.TestCase):
    def walls(self, plain, bgzf):
        return {("big", "C", "plain", 16): [plain], ("big", "C", "bgzf", 16): [bgzf]}

    def test_floor_is_slower_mate_of_fastest_single_thread_tool(self):
        rows = [base_row("1", 50), base_row("1", 40, tool="igzip"), base_row("2", 45),
                base_row("2", 5, tool="igzip", result="ABSENT")]  # ABSENT must be ignored
        self.assertEqual(a.decode_floor(rows, "big"), 45.0)

    def test_floor_none_when_a_mate_is_missing(self):
        self.assertIsNone(a.decode_floor([base_row("1", 50)], "big"))
        rows = [base_row("1", 50), base_row("2", "", result="EXIT1")]
        self.assertIsNone(a.decode_floor(rows, "big"))

    def test_floor_none_without_data(self):
        self.assertIsNone(a.decode_floor([], "big"))

    def test_propose_when_decode_bound_and_bgzf_helps(self):
        verdict, _ = a.decide(self.walls(60, 20), 50.0, "big")
        self.assertTrue(verdict.startswith("PROPOSE"))

    def test_do_not_propose_when_not_decode_bound(self):
        verdict, _ = a.decide(self.walls(60, 20), 20.0, "big")
        self.assertTrue(verdict.startswith("DO NOT PROPOSE"))

    def test_do_not_propose_when_bgzf_does_not_help(self):
        verdict, _ = a.decide(self.walls(60, 50), 55.0, "big")
        self.assertTrue(verdict.startswith("DO NOT PROPOSE"))

    def test_inconclusive_when_data_missing(self):
        verdict, _ = a.decide({("big", "C", "plain", 16): [60]}, 50.0, "big")
        self.assertTrue(verdict.startswith("INCONCLUSIVE"))
        verdict, _ = a.decide(self.walls(60, 20), None, "big")
        self.assertTrue(verdict.startswith("INCONCLUSIVE"))

    def test_mismatch_detected_across_formats(self):
        rows = [bench_row("plain", 10, reads="100"), bench_row("bgzf", 5, reads="99")]
        self.assertEqual(len(a.find_mismatches(rows)), 1)
        rows = [bench_row("plain", 10, digest="aa"), bench_row("bgzf", 5, digest="bb")]
        self.assertEqual(len(a.find_mismatches(rows)), 1)
        rows = [bench_row("plain", 10), bench_row("bgzf", 5)]
        self.assertEqual(a.find_mismatches(rows), [])

    def test_failed_runs_are_not_compared(self):
        rows = [bench_row("plain", 10, reads="100"), bench_row("bgzf", 0, reads="-", result="HUNG")]
        self.assertEqual(a.find_mismatches(rows), [])

    def test_partial_failure_makes_decide_inconclusive(self):
        f = {("big", "C", "plain", 16): ["HUNG", "EXIT1"]}
        verdict, detail = a.decide(self.walls(60, 20), 50.0, "big", f)
        self.assertTrue(verdict.startswith("INCONCLUSIVE"))
        self.assertIn("HUNG", detail)
        self.assertIn("2 of 3", detail)

    def test_failure_cells(self):
        k = ("big", "C", "plain", 16)
        self.assertEqual(a.wall_cell(k, {k: [10.0]}, {k: ["HUNG", "HUNG"]}), "10.0 (2/3 failed)")
        self.assertEqual(a.wall_cell(k, {}, {k: ["HUNG"] * 3}), "FAILED (3/3)")
        self.assertEqual(a.wall_cell(k, {}, {}), "-")

    def run_main(self, rows, *extra):
        import subprocess, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_gzip_vs_bgzf.py")
        hdr = "dataset\tformat\tmode\tthreads\tresult\twall_s\tmax_thread_cpu_frac\treads_after\tdigest\n"
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write(hdr)
            for r in rows:
                f.write("\t".join(r[c] for c in ("dataset", "format", "mode", "threads", "result", "wall_s",
                                                  "max_thread_cpu_frac", "reads_after", "digest")) + "\n")
        try:
            return subprocess.run([sys.executable, script, f.name, *extra], capture_output=True, text=True)
        finally:
            os.unlink(f.name)

    def test_partial_failure_and_all_failed_rendered_by_main(self):
        rows = [bench_row("plain", 10), bench_row("plain", 0, result="HUNG"),
                bench_row("bgzf", 0, result="EXIT2"), bench_row("bgzf", 0, result="EXIT2")]
        r = self.run_main(rows)
        self.assertEqual(r.returncode, 0)
        self.assertIn("10.0 (1/2 failed)", r.stdout)
        self.assertIn("FAILED (2/2)", r.stdout)
        self.assertIn("### Failed runs", r.stdout)
        self.assertIn("EXIT2", r.stdout)

    def test_verdict_invalid_on_mismatch(self):
        r = self.run_main([bench_row("plain", 10, reads="100"), bench_row("bgzf", 5, reads="99")],
                          "--large", "big")
        self.assertEqual(r.returncode, 1)
        self.assertIn("INVALID: plain and BGZF outputs differ", r.stdout)
        self.assertNotIn("PROPOSE", r.stdout)
        self.assertIn("('bgzf', '99')", r.stdout)

    def test_one_format_group_is_not_compared(self):
        r = self.run_main([bench_row("plain", 10), bench_row("plain", 10, t=8), bench_row("bgzf", 5, t=8)])
        self.assertEqual(r.returncode, 0)
        self.assertIn("### Not compared", r.stdout)
        self.assertIn("only plain", r.stdout)
        self.assertIn("1 groups compared; 1 groups not compared", r.stdout)

    def test_digest_for_one_format_only_is_not_a_mismatch(self):
        rows = [bench_row("plain", 10, digest="aa"), bench_row("bgzf", 5, digest="-")]
        self.assertEqual(a.find_mismatches(rows), [])
        mism, n, nc = a.compare_outputs(rows)
        self.assertEqual((mism, n), ([], 1))
        self.assertIn("digest present only for plain", nc[0][3])
        self.assertEqual(self.run_main(rows).returncode, 0)

    def test_main_reports_bad_input_without_traceback(self):
        import subprocess, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_gzip_vs_bgzf.py")
        r = subprocess.run([sys.executable, script, "/nonexistent.tsv"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("dataset\tformat\tmode\tthreads\tresult\twall_s\tmax_thread_cpu_frac\treads_after\tdigest\n"
                    "big\tplain\tC\t16\tOK\tabc\t0.9\t1\t-\n")
        r = subprocess.run([sys.executable, script, f.name], capture_output=True, text=True)
        os.unlink(f.name)
        self.assertEqual(r.returncode, 2)
        self.assertIn("non-numeric", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_large_dataset_without_data_is_inconclusive(self):
        import subprocess, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_gzip_vs_bgzf.py")
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("dataset\tformat\tmode\tthreads\tresult\twall_s\tmax_thread_cpu_frac\treads_after\tdigest\n")
        r = subprocess.run([sys.executable, script, f.name, "--large", "nope"], capture_output=True, text=True)
        os.unlink(f.name)
        self.assertEqual(r.returncode, 0)
        self.assertIn("INCONCLUSIVE", r.stdout)


if __name__ == "__main__":
    unittest.main()
