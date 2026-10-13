#!/usr/bin/env python3
"""Summarize the gzip-vs-BGZF benchmark and apply the decision rule from
benchmark/gzip-vs-bgzf-design.md.

Usage: analyze_gzip_vs_bgzf.py <bench.tsv> [baseline.tsv] [--large DATASET]
Exit status 2 on unreadable/malformed input; 1 if plain and BGZF runs disagree on output (reads_after or digest).
"""
import argparse
import csv
import statistics
import sys
from collections import defaultdict

DECODE_BOUND_SLACK = 1.30  # plain wall within 30% of the single-thread decode floor
MIN_BGZF_SPEEDUP = 1.5
RULE_MODE, RULE_THREADS = "C", 16
FLOOR_TOOL = "igzip"  # fastp decodes plain gzip with ISA-L, so igzip is the like-for-like floor
NO_FLOOR = "igzip decode baseline missing: install isa-l's igzip"


def med(xs):
    return statistics.median(xs) if xs else None


class InputError(Exception):
    pass


BENCH_COLS = {"dataset", "format", "mode", "threads", "cache", "result", "wall_s", "max_thread_cpu_frac",
              "reads_after", "digest"}
BASE_COLS = {"dataset", "mate", "variant", "tool", "threads", "cache", "result", "wall_s"}


def load(path, cols):
    try:
        with open(path, newline="") as f:
            rd = csv.DictReader(f, delimiter="\t")
            missing = cols - set(rd.fieldnames or [])
            if missing:
                raise InputError(f"{path}: missing column(s) {sorted(missing)}")
            return list(rd)
    except OSError as e:
        raise InputError(f"cannot read {path}: {e.strerror}")


def num(row, col, path):
    try:
        return float(row[col])
    except (TypeError, ValueError):
        raise InputError(f"{path}: non-numeric {col}={row[col]!r} in an OK row ({row.get('dataset')}, "
                         f"{row.get('mode') or row.get('mate')}, {row.get('format') or row.get('variant')}, "
                         f"threads {row.get('threads')})")


def decode_floor(baseline, ds, tool=FLOOR_TOOL):
    """Slower mate's fastest single-thread plain-gzip decode time with `tool` (PE runs one reader per mate)."""
    per_mate = defaultdict(list)
    for r in baseline:
        if (r["dataset"] == ds and r["tool"] == tool and r["variant"] == "plain" and r["threads"] == "1"
                and r["result"] == "OK" and r["wall_s"]):
            per_mate[r["mate"]].append(num(r, "wall_s", "baseline"))
    if not {"1", "2"} <= set(per_mate):  # a missing mate would understate the floor
        return None
    return max(min(v) for v in per_mate.values())


def rule_failures(walls, failures, ds):
    """Describe failed reps in the decision-rule cells (plain and BGZF, mode C, -w 16)."""
    out = []
    for fmt in ("plain", "bgzf"):
        k = (ds, RULE_MODE, fmt, RULE_THREADS)
        bad = failures.get(k, [])
        if bad:
            out.append(f"{fmt}: {len(bad)} of {len(bad) + len(walls.get(k, []))} runs failed ({', '.join(sorted(bad))})")
    return out


def decide(walls, floor, ds, failures=None):
    failures = failures or {}
    bad = rule_failures(walls, failures, ds)
    if bad:
        return (f"INCONCLUSIVE: failed runs in the decision cell (mode {RULE_MODE}, -w {RULE_THREADS})",
                "; ".join(bad))
    plain = med(walls.get((ds, RULE_MODE, "plain", RULE_THREADS), []))
    bgzf = med(walls.get((ds, RULE_MODE, "bgzf", RULE_THREADS), []))
    if plain is None or bgzf is None or floor is None:
        return ("INCONCLUSIVE: missing plain, BGZF or decode-floor data "
                f"for mode {RULE_MODE} at -w {RULE_THREADS}", NO_FLOOR if floor is None else "")
    bound = plain <= floor * DECODE_BOUND_SLACK
    if bgzf <= 0 or floor <= 0:
        return ("INCONCLUSIVE: non-positive BGZF wall time or decode floor", "")
    gain = plain / bgzf
    detail = (f"plain {plain:.1f}s, BGZF {bgzf:.1f}s ({gain:.2f}x), decode floor {floor:.1f}s "
              f"(plain/floor {plain / floor:.2f}; decode-bound means <= {DECODE_BOUND_SLACK:.2f})")
    if bound and gain >= MIN_BGZF_SPEEDUP:
        return ("PROPOSE a plain-gzip parallel reader upstream", detail)
    return ("DO NOT PROPOSE a reader; recommend BGZF on ingest", detail)


def compare_outputs(bench):
    """Compare plain vs BGZF output per (dataset, mode, threads) over OK runs.

    Returns (mismatches, n_compared, not_compared, n_digest). mismatches: (dataset, mode, threads, field,
    sorted [(format, value)]). not_compared: (dataset, mode, threads, reason) -- never a pass.
    n_digest: compared groups whose digest was also compared (reads_after is compared for all)."""
    groups = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))  # g -> fmt -> field -> values
    for r in bench:
        if r["result"] != "OK":
            continue
        g = (r["dataset"], r["mode"], int(num(r, "threads", "bench")))
        groups[g][r["format"]]["reads_after"].add(r["reads_after"])
        if r["digest"] not in ("", "-"):
            groups[g][r["format"]]["digest"].add(r["digest"])
    mism, nc, compared, n_digest = [], [], 0, 0
    for g in sorted(groups):
        fmts = groups[g]
        if not {"plain", "bgzf"} <= set(fmts):
            nc.append((*g, f"only {'/'.join(sorted(fmts))} has OK runs"))
            continue
        compared += 1
        for field in ("reads_after", "digest"):
            per = {f: fmts[f][field] for f in ("plain", "bgzf")}
            if field == "digest" and not (per["plain"] and per["bgzf"]):
                if per["plain"] or per["bgzf"]:
                    nc.append((*g, f"digest present only for {'plain' if per['plain'] else 'bgzf'}"))
                continue
            n_digest += field == "digest"
            if len(per["plain"] | per["bgzf"]) > 1:
                mism.append((*g, field, sorted((f, v) for f, vs in per.items() for v in vs)))
    return mism, compared, nc, n_digest


def find_mismatches(bench):
    return compare_outputs(bench)[0]


THREAD_CAVEAT = ("fastp does not name its threads; the reader thread is inferred from the two busiest threads, "
                 "not observed (build with the pack-trace thread names from fork PR #11 to observe it)")


def second_frac(top):
    """Second-busiest thread's CPU fraction from run_timed.py's thread_cpu_top (tid:comm:frac,...)."""
    parts = (top or "NA").split(",")
    if len(parts) < 2:
        return None
    try:
        return float(parts[1].rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return None


def cache_states(rows):
    return sorted({r["cache"] for r in rows if r["result"] == "OK"})


def report_cache(bench, baseline, have_baseline):
    """Print the cache states of the timed runs; warn when fastp runs and baselines differ."""
    b = cache_states(bench)
    line = f"Cache state: bench {', '.join(b) or 'none'}"
    if have_baseline:
        d = cache_states(baseline)
        line += f"; baseline {', '.join(d) or 'none'}"
        if b != d:
            line += (f"\n\n**WARNING: cache state differs between fastp runs and decode baselines "
                     f"(bench {'/'.join(b)} vs baseline {'/'.join(d)}); plain / floor is not like-for-like.**")
    print(line + "\n")


def cell(v, f):
    return f.format(v) if v is not None else "-"


def wall_cell(k, walls, failures):
    ok, bad = walls.get(k, []), failures.get(k, [])
    if not ok and not bad:
        return "-"
    if not ok:
        return f"FAILED ({len(bad)}/{len(bad)})"
    if bad:
        return f"{med(ok):.1f} ({len(bad)}/{len(ok) + len(bad)} failed)"
    return f"{med(ok):.1f}"


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("bench")
    ap.add_argument("baseline", nargs="?")
    ap.add_argument("--large", help="dataset the decision rule is evaluated on")
    args = ap.parse_args()

    bench = load(args.bench, BENCH_COLS)
    baseline = load(args.baseline, BASE_COLS) if args.baseline else []
    walls, fracs, fracs2, failures = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for r in bench:
        k = (r["dataset"], r["mode"], r["format"], int(num(r, "threads", args.bench)))
        if r["result"] == "OK":
            walls[k].append(num(r, "wall_s", args.bench))
            if r["max_thread_cpu_frac"] not in ("", "NA"):
                fracs[k].append(num(r, "max_thread_cpu_frac", args.bench))
            f2 = second_frac(r.get("thread_cpu_top"))  # column is absent in older result files
            if f2 is not None:
                fracs2[k].append(f2)
        else:
            failures[k].append(r["result"])

    report_cache(bench, baseline, bool(args.baseline))
    keys = set(walls) | set(failures)
    for ds in sorted({k[0] for k in keys}):
        floor = decode_floor(baseline, ds)
        print(f"## {ds}\n")
        print("Single-thread decode floor: "
              + (f"{floor:.1f}s ({FLOOR_TOOL} -dc, slower mate)" if floor else f"not measured ({NO_FLOOR})"))
        gz = decode_floor(baseline, ds, "gzip")
        if gz:
            print(f"gzip -dc single-thread (informational, not the floor): {gz:.1f}s")
        print()
        for mode in sorted({k[1] for k in keys if k[0] == ds}):
            print(f"### mode {mode}\n")
            # paired-end has one reader per mate, so two near-saturated threads are expected
            print("| -w | plain s | BGZF s | BGZF speedup | plain busiest-thread CPU "
                  "| plain 2nd-busiest thread CPU | plain / floor |")
            print("|---|---|---|---|---|---|---|")
            for t in sorted({k[3] for k in keys if k[:2] == (ds, mode)}):
                p = med(walls.get((ds, mode, "plain", t), []))
                b = med(walls.get((ds, mode, "bgzf", t), []))
                fr = med(fracs.get((ds, mode, "plain", t), []))
                fr2 = med(fracs2.get((ds, mode, "plain", t), []))
                print(f"| {t} | {wall_cell((ds, mode, 'plain', t), walls, failures)} | "
                      f"{wall_cell((ds, mode, 'bgzf', t), walls, failures)} | "
                      f"{cell(p / b if p and b else None, '{:.2f}x')} | {cell(fr, '{:.2f}')} | {cell(fr2, '{:.2f}')} | "
                      f"{cell(p / floor if p and floor else None, '{:.2f}')} |")
            print(f"\n{THREAD_CAVEAT}\n")
        bad = sorted((k, v) for k, v in failures.items() if k[0] == ds)
        if bad:
            print("### Failed runs\n")
            for k, v in bad:
                print(f"- mode {k[1]}, {k[2]}, -w {k[3]}: {len(v)} failed ({', '.join(sorted(v))})")
            print()

    mism, n_cmp, not_cmp, n_digest = compare_outputs(bench)
    if args.large:
        if mism:
            print(f"## Decision ({args.large})\n\n**INVALID: plain and BGZF outputs differ, "
                  "timings cannot be compared**\n")
        else:
            verdict, detail = decide(walls, decode_floor(baseline, args.large), args.large, failures)
            print(f"## Decision ({args.large})\n\n**{verdict}**\n\n{detail}\n")

    print("## Output agreement between plain and BGZF\n")
    if not_cmp:
        print("### Not compared\n")
        for *g, why in not_cmp:
            print(f"- {g[0]}, mode {g[1]}, -w {g[2]}: {why}")
        print()
    if mism:
        print("**MISMATCHES FOUND:**\n")
        for m in mism:
            print(f"- {m}")
        sys.exit(1)
    n_groups = len({tuple(x[:3]) for x in not_cmp})
    fields = (f"reads_after for all; digest for {n_digest}" if n_digest
              else "reads_after only; digest not run")
    print(f"No mismatches among the {n_cmp} groups compared ({fields}); {n_groups} groups not compared.")


def main():
    try:
        run()
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
