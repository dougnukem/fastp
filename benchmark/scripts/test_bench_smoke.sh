#!/bin/bash
# benchmark/scripts/test_bench_smoke.sh -- needs a fastp binary: FASTP=/path/to/fastp bash test_bench_smoke.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
[ -x "${FASTP:-}" ] || { echo "SKIP: set FASTP to a built fastp binary"; exit 0; }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
for m in 1 2; do
  gzip -c "$ROOT/testdata/R$m.fq" > "$T/smoke_R$m.fastq.gz"
  bash "$HERE/make_variants.sh" "$T/smoke_R$m.fastq.gz" "$T/data" 6 2 >/dev/null
done

bash "$HERE/bench_gzip_vs_bgzf.sh" "$FASTP" "$T/data" "$T/out.tsv" "1,2" 1 60 smoke >/dev/null 2>"$T/err.log"

rows=$(($(wc -l < "$T/out.tsv") - 1))
[ "$rows" = 12 ] || { echo "expected 12 rows (2 formats x 3 modes x 2 thread counts), got $rows"; exit 1; }
head -1 "$T/out.tsv" | grep -q $'^dataset\tformat\tmode\tthreads\trep\tbgzf_budget\tcache\tresult\twall_s' || { echo "bad header"; exit 1; }
bad=$(awk -F'\t' 'NR>1 && $8!="OK"' "$T/out.tsv" | wc -l | tr -d ' ')
[ "$bad" = 0 ] || { echo "non-OK rows:"; awk -F'\t' 'NR>1 && $8!="OK"' "$T/out.tsv"; exit 1; }
# both formats must produce the same read count for every (mode, threads)
d=$(awk -F'\t' 'NR>1{print $3,$4,$14}' "$T/out.tsv" | sort -u | awk '{print $1,$2}' | uniq -d | wc -l | tr -d ' ')
[ "$d" = 0 ] || { echo "plain and bgzf disagree on reads_after"; exit 1; }
# missing input is skipped, not recorded
bash "$HERE/bench_gzip_vs_bgzf.sh" "$FASTP" "$T/data" "$T/out2.tsv" "1" 1 60 nosuch >/dev/null 2>"$T/err2.log"
[ "$(($(wc -l < "$T/out2.tsv") - 1))" = 0 ] && grep -q "skip nosuch" "$T/err2.log" || { echo "missing input not skipped"; exit 1; }
echo PASS
