# benchmark/scripts/test_analyze_gzip_vs_bgzf.py
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_gzip_vs_bgzf as a

BENCH_COLS = ("dataset", "format", "mode", "threads", "cache", "result", "wall_s", "max_thread_cpu_frac",
              "reads_after", "digest")
BASE_COLS = ("dataset", "mate", "variant", "tool", "threads", "cache", "result", "wall_s", "uncompressed_bytes")

def bench_row(fmt, wall, t=16, mode="C", reads="100", digest="-", ds="big", result="OK", cache="not_dropped"):
    return dict(dataset=ds, format=fmt, mode=mode, threads=str(t), cache=cache, result=result, wall_s=str(wall),
                max_thread_cpu_frac="0.99", reads_after=reads, digest=digest)


def base_row(mate, wall, variant="plain", tool="igzip", t="1", result="OK", ds="big", cache="not_dropped"):
    return dict(dataset=ds, mate=mate, variant=variant, tool=tool, threads=t, cache=cache, result=result,
                wall_s=str(wall), uncompressed_bytes="1")


class AnalyzeTest(unittest.TestCase):
    def walls(self, plain, bgzf):
        return {("big", "C", "plain", 16): [plain], ("big", "C", "bgzf", 16): [bgzf]}

    def test_floor_is_slower_mate_single_thread_igzip(self):
        rows = [base_row("1", 50), base_row("1", 40), base_row("2", 45),
                base_row("2", 5, result="ABSENT")]  # ABSENT must be ignored
        self.assertEqual(a.decode_floor(rows, "big"), 45.0)

    def test_floor_comes_from_igzip_even_when_gzip_is_faster(self):
        rows = [base_row("1", 50), base_row("2", 45),
                base_row("1", 10, tool="gzip"), base_row("2", 10, tool="gzip")]
        self.assertEqual(a.decode_floor(rows, "big"), 50.0)

    def test_gzip_only_baseline_gives_no_floor(self):
        rows = [base_row("1", 50, tool="gzip"), base_row("2", 45, tool="gzip"),
                base_row("1", "", result="ABSENT"), base_row("2", "", result="ABSENT")]
        self.assertIsNone(a.decode_floor(rows, "big"))

    def test_missing_igzip_floor_detail_says_install_igzip(self):
        verdict, detail = a.decide(self.walls(60, 20), None, "big")
        self.assertTrue(verdict.startswith("INCONCLUSIVE"))
        self.assertIn("igzip decode baseline missing: install isa-l's igzip", detail)

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

    @staticmethod
    def write_tsv(rows, cols):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("\t".join(cols) + "\n")
            for r in rows:
                f.write("\t".join(r[c] for c in cols) + "\n")
        return f.name

    def run_main(self, rows, *extra, baseline=None, bench_cols=BENCH_COLS):
        import subprocess
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_gzip_vs_bgzf.py")
        files = [self.write_tsv(rows, bench_cols)]
        if baseline is not None:
            files.append(self.write_tsv(baseline, BASE_COLS))
        try:
            return subprocess.run([sys.executable, script, *files, *extra], capture_output=True, text=True)
        finally:
            for p in files:
                os.unlink(p)

    def test_summary_names_the_floor_tool_and_shows_gzip_as_informational(self):
        base = [base_row("1", 50), base_row("2", 45),
                base_row("1", 12, tool="gzip"), base_row("2", 11, tool="gzip")]
        r = self.run_main([bench_row("plain", 60), bench_row("bgzf", 20)], "--large", "big", baseline=base)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Single-thread decode floor: 50.0s (igzip -dc", r.stdout)
        self.assertIn("gzip -dc single-thread (informational, not the floor): 12.0s", r.stdout)

    def test_cache_states_printed_and_warned_when_they_differ(self):
        base = [base_row("1", 50), base_row("2", 45)]
        bench = [bench_row("plain", 60, cache="cold"), bench_row("bgzf", 20, cache="cold")]
        r = self.run_main(bench, baseline=base)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Cache state: bench cold; baseline not_dropped", r.stdout)
        self.assertIn("WARNING: cache state differs between fastp runs and decode baselines", r.stdout)

    def test_no_cache_warning_when_states_match(self):
        base = [base_row("1", 50, cache="cold"), base_row("2", 45, cache="cold")]
        r = self.run_main([bench_row("plain", 60, cache="cold"), bench_row("bgzf", 20, cache="cold")],
                          baseline=base)
        self.assertIn("Cache state: bench cold; baseline cold", r.stdout)
        self.assertNotIn("WARNING", r.stdout)

    def test_second_busiest_thread_and_caveat(self):
        rows = [bench_row("plain", 60), bench_row("bgzf", 20)]
        rows[0]["thread_cpu_top"] = "101:fastp:0.980,102:fastp:0.950,103:fastp:0.200"
        rows[1]["thread_cpu_top"] = "NA"
        r = self.run_main(rows, bench_cols=BENCH_COLS + ("thread_cpu_top",))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("plain 2nd-busiest thread CPU", r.stdout)
        self.assertIn("| 0.99 | 0.95 |", r.stdout)
        self.assertIn("fastp does not name its threads; the reader thread is inferred from the two busiest "
                      "threads, not observed (build with the pack-trace thread names from fork PR #11 to "
                      "observe it)", r.stdout)

    def test_second_busiest_absent_without_column(self):
        r = self.run_main([bench_row("plain", 60), bench_row("bgzf", 20)])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("| 0.99 | - |", r.stdout)

    def test_second_frac(self):
        self.assertEqual(a.second_frac("1:fastp:0.9,2:fastp:0.8"), 0.8)
        self.assertIsNone(a.second_frac("1:fastp:0.9"))
        self.assertIsNone(a.second_frac("NA"))
        self.assertIsNone(a.second_frac(None))

    def test_summary_without_igzip_says_install_it(self):
        base = [base_row("1", 12, tool="gzip"), base_row("2", 11, tool="gzip")]
        r = self.run_main([bench_row("plain", 60), bench_row("bgzf", 20)], "--large", "big", baseline=base)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("INCONCLUSIVE", r.stdout)
        self.assertIn("igzip decode baseline missing: install isa-l's igzip", r.stdout)

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
        self.assertIn("No mismatches among the 1 groups compared (reads_after only; digest not run); "
                      "1 groups not compared", r.stdout)

    def test_agreement_line_names_fields_compared(self):
        rows = [bench_row("plain", 10, digest="aa"), bench_row("bgzf", 5, digest="aa"),
                bench_row("plain", 10, mode="A"), bench_row("bgzf", 5, mode="A")]
        r = self.run_main(rows)
        self.assertIn("No mismatches among the 2 groups compared (reads_after for all; digest for 1)", r.stdout)

    def test_digest_for_one_format_only_is_not_a_mismatch(self):
        rows = [bench_row("plain", 10, digest="aa"), bench_row("bgzf", 5, digest="-")]
        self.assertEqual(a.find_mismatches(rows), [])
        mism, n, nc, n_digest = a.compare_outputs(rows)
        self.assertEqual((mism, n, n_digest), ([], 1, 0))
        self.assertIn("digest present only for plain", nc[0][3])
        self.assertEqual(self.run_main(rows).returncode, 0)

    def test_main_reports_bad_input_without_traceback(self):
        import subprocess, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_gzip_vs_bgzf.py")
        r = subprocess.run([sys.executable, script, "/nonexistent.tsv"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("dataset\tformat\tmode\tthreads\tcache\tresult\twall_s\tmax_thread_cpu_frac\treads_after\tdigest\n"
                    "big\tplain\tC\t16\tcold\tOK\tabc\t0.9\t1\t-\n")
        r = subprocess.run([sys.executable, script, f.name], capture_output=True, text=True)
        os.unlink(f.name)
        self.assertEqual(r.returncode, 2)
        self.assertIn("non-numeric", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_large_dataset_without_data_is_inconclusive(self):
        import subprocess, tempfile
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_gzip_vs_bgzf.py")
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
            f.write("dataset\tformat\tmode\tthreads\tcache\tresult\twall_s\tmax_thread_cpu_frac\treads_after\tdigest\n")
        r = subprocess.run([sys.executable, script, f.name, "--large", "nope"], capture_output=True, text=True)
        os.unlink(f.name)
        self.assertEqual(r.returncode, 0)
        self.assertIn("INCONCLUSIVE", r.stdout)


if __name__ == "__main__":
    unittest.main()
