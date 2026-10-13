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
# digest: present for every mode-C row, absent ("-") for A/B, and equal across formats per thread count
nd=$(awk -F'\t' 'NR>1 && $3=="C" && ($15 !~ /^[0-9a-f]+_[0-9a-f]+$/ || length($15) != 25)' "$T/out.tsv" | wc -l | tr -d ' ')
[ "$nd" = 0 ] || { echo "mode C rows without a digest"; exit 1; }
nab=$(awk -F'\t' 'NR>1 && $3!="C" && $15!="-"' "$T/out.tsv" | wc -l | tr -d ' ')
[ "$nab" = 0 ] || { echo "mode A/B rows must have digest '-'"; exit 1; }
nc=$(awk -F'\t' 'NR>1 && $3=="C"{print $4,$15}' "$T/out.tsv" | sort -u | awk '{print $1}' | uniq -d | wc -l | tr -d ' ')
[ "$nc" = 0 ] || { echo "plain and bgzf output digests differ"; exit 1; }
[ "$(awk -F'\t' 'NR>1 && $3=="C"' "$T/out.tsv" | wc -l | tr -d ' ')" = 4 ] || { echo "expected 4 mode C rows"; exit 1; }
# a fastp that fails must give a non-OK row and a non-zero exit, not a dropped row
printf '#!/bin/sh\nexit 2\n' > "$T/badfastp"; chmod +x "$T/badfastp"
rc=0; bash "$HERE/bench_gzip_vs_bgzf.sh" "$T/badfastp" "$T/data" "$T/out3.tsv" "1" 1 60 smoke >/dev/null 2>"$T/err3.log" || rc=$?
[ "$rc" != 0 ] || { echo "failing fastp must exit non-zero"; exit 1; }
[ "$(awk -F'\t' 'NR>1' "$T/out3.tsv" | wc -l | tr -d ' ')" = 6 ] || { echo "failing fastp must still record 6 rows"; exit 1; }
[ "$(awk -F'\t' 'NR>1 && $8=="EXIT2"' "$T/out3.tsv" | wc -l | tr -d ' ')" = 6 ] || { echo "rows not marked EXIT2"; exit 1; }
grep -q "6 run(s) did not complete" "$T/err3.log" || { echo "missing failure summary"; exit 1; }
# missing input is skipped, not recorded
bash "$HERE/bench_gzip_vs_bgzf.sh" "$FASTP" "$T/data" "$T/out2.tsv" "1" 1 60 nosuch >/dev/null 2>"$T/err2.log"
[ "$(($(wc -l < "$T/out2.tsv") - 1))" = 0 ] && grep -q "skip nosuch" "$T/err2.log" || { echo "missing input not skipped"; exit 1; }
# decode baselines: gzip always runs; an absent tool is ABSENT with an empty wall time, never 0
rc=0; bash "$HERE/decode_baseline.sh" "$T/data" "$T/base.tsv" "1,2" smoke >/dev/null 2>"$T/berr.log" || rc=$?
[ "$rc" = 0 ] || { echo "decode_baseline failed (rc=$rc)"; cat "$T/berr.log"; exit 1; }
head -1 "$T/base.tsv" | grep -q $'^dataset\tmate\tvariant\ttool\tthreads\tresult\twall_s\tuncompressed_bytes' || { echo "bad baseline header"; exit 1; }
ok=$(awk -F'\t' 'NR>1 && $4=="gzip" && $6=="OK" && $7!=""' "$T/base.tsv" | wc -l | tr -d ' ')
[ "$ok" = 4 ] || { echo "expected 4 gzip OK rows (2 mates x 2 variants), got $ok"; exit 1; }
bg=$(awk -F'\t' 'NR>1 && $4=="bgzip" && $3=="bgzf" && $6=="OK"' "$T/base.tsv" | wc -l | tr -d ' ')
[ "$bg" = 4 ] || { echo "expected 4 bgzip OK rows (2 mates x 2 thread counts), got $bg"; exit 1; }
[ "$(awk -F'\t' 'NR>1 && $4=="bgzip" && $3=="plain"' "$T/base.tsv" | wc -l | tr -d ' ')" = 0 ] || { echo "bgzip must only run on the bgzf variant"; exit 1; }
awk -F'\t' 'NR>1 && $6=="ABSENT" && $7!=""{bad=1} END{exit bad}' "$T/base.tsv" || { echo "ABSENT row has a wall time"; exit 1; }
awk -F'\t' 'NR>1 && $8 !~ /^[1-9][0-9]*$/{bad=1} END{exit bad}' "$T/base.tsv" || { echo "uncompressed_bytes missing or zero"; exit 1; }
# an installed tool that fails must give an EXIT row with an empty wall time and a non-zero exit
mkdir "$T/stub"; printf '#!/bin/sh\nexit 3\n' > "$T/stub/igzip"; chmod +x "$T/stub/igzip"
rc=0; PATH="$T/stub:$PATH" bash "$HERE/decode_baseline.sh" "$T/data" "$T/base2.tsv" "1" smoke >/dev/null 2>"$T/berr2.log" || rc=$?
[ "$rc" != 0 ] || { echo "failing igzip must exit non-zero"; exit 1; }
[ "$(awk -F'\t' 'NR>1 && $4=="igzip" && $6=="EXIT3" && $7==""' "$T/base2.tsv" | wc -l | tr -d ' ')" = 4 ] || { echo "igzip rows not EXIT3 with empty wall"; exit 1; }
grep -q "4 run(s) did not complete" "$T/berr2.log" || { echo "missing baseline failure summary"; exit 1; }
echo PASS
