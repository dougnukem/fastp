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


def med(xs):
    return statistics.median(xs) if xs else None


class InputError(Exception):
    pass


BENCH_COLS = {"dataset", "format", "mode", "threads", "result", "wall_s", "max_thread_cpu_frac",
              "reads_after", "digest"}
BASE_COLS = {"dataset", "mate", "variant", "threads", "result", "wall_s"}


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


def decode_floor(baseline, ds):
    """Slower mate's fastest single-thread plain-gzip decode time (PE runs one reader per mate)."""
    per_mate = defaultdict(list)
    for r in baseline:
        if (r["dataset"] == ds and r["variant"] == "plain" and r["threads"] == "1"
                and r["result"] == "OK" and r["wall_s"]):
            per_mate[r["mate"]].append(num(r, "wall_s", "baseline"))
    if not {"1", "2"} <= set(per_mate):  # a missing mate would understate the floor
        return None
    return max(min(v) for v in per_mate.values())


def decide(walls, floor, ds):
    plain = med(walls.get((ds, RULE_MODE, "plain", RULE_THREADS), []))
    bgzf = med(walls.get((ds, RULE_MODE, "bgzf", RULE_THREADS), []))
    if plain is None or bgzf is None or floor is None:
        return ("INCONCLUSIVE: missing plain, BGZF or decode-floor data "
                f"for mode {RULE_MODE} at -w {RULE_THREADS}", "")
    bound = plain <= floor * DECODE_BOUND_SLACK
    if bgzf <= 0 or floor <= 0:
        return ("INCONCLUSIVE: non-positive BGZF wall time or decode floor", "")
    gain = plain / bgzf
    detail = (f"plain {plain:.1f}s, BGZF {bgzf:.1f}s ({gain:.2f}x), decode floor {floor:.1f}s "
              f"(plain/floor {plain / floor:.2f}; decode-bound means <= {DECODE_BOUND_SLACK:.2f})")
    if bound and gain >= MIN_BGZF_SPEEDUP:
        return ("PROPOSE a plain-gzip parallel reader upstream", detail)
    return ("DO NOT PROPOSE a reader; recommend BGZF on ingest", detail)


def find_mismatches(bench):
    """(dataset, mode, threads, field, values) where plain and BGZF disagree. Failed runs are skipped."""
    seen = defaultdict(lambda: defaultdict(set))
    for r in bench:
        if r["result"] != "OK":
            continue
        g = (r["dataset"], r["mode"], int(num(r, "threads", "bench")))
        seen[g]["reads_after"].add(r["reads_after"])
        if r["digest"] not in ("", "-"):
            seen[g]["digest"].add(r["digest"])
    return [(*g, field, vals) for g, fields in seen.items() for field, vals in fields.items() if len(vals) > 1]


def run():
    ap = argparse.ArgumentParser()
    ap.add_argument("bench")
    ap.add_argument("baseline", nargs="?")
    ap.add_argument("--large", help="dataset the decision rule is evaluated on")
    args = ap.parse_args()

    bench = load(args.bench, BENCH_COLS)
    baseline = load(args.baseline, BASE_COLS) if args.baseline else []
    walls, fracs = defaultdict(list), defaultdict(list)
    for r in bench:
        if r["result"] == "OK":
            k = (r["dataset"], r["mode"], r["format"], int(num(r, "threads", args.bench)))
            walls[k].append(num(r, "wall_s", args.bench))
            if r["max_thread_cpu_frac"] not in ("", "NA"):
                fracs[k].append(num(r, "max_thread_cpu_frac", args.bench))

    for ds in sorted({k[0] for k in walls}):
        floor = decode_floor(baseline, ds)
        print(f"## {ds}\n")
        print("Single-thread decode floor: " + (f"{floor:.1f}s" if floor else "not measured") + "\n")
        for mode in sorted({k[1] for k in walls if k[0] == ds}):
            print(f"### mode {mode}\n")
            print("| -w | plain s | BGZF s | BGZF speedup | plain busiest-thread CPU | plain / floor |")
            print("|---|---|---|---|---|---|")
            for t in sorted({k[3] for k in walls if k[:2] == (ds, mode)}):
                p = med(walls.get((ds, mode, "plain", t), []))
                b = med(walls.get((ds, mode, "bgzf", t), []))
                fr = med(fracs.get((ds, mode, "plain", t), []))
                cell = lambda v, f: f.format(v) if v is not None else "-"
                print(f"| {t} | {cell(p, '{:.1f}')} | {cell(b, '{:.1f}')} | "
                      f"{cell(p / b if p and b else None, '{:.2f}x')} | {cell(fr, '{:.2f}')} | "
                      f"{cell(p / floor if p and floor else None, '{:.2f}')} |")
            print()

    if args.large:
        verdict, detail = decide(walls, decode_floor(baseline, args.large), args.large)
        print(f"## Decision ({args.large})\n\n**{verdict}**\n\n{detail}\n")

    mism = find_mismatches(bench)
    print("## Output agreement between plain and BGZF\n")
    if mism:
        print("**MISMATCHES FOUND:**\n")
        for m in mism:
            print(f"- {m}")
        sys.exit(1)
    print("No mismatches.")


def main():
    try:
        run()
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
