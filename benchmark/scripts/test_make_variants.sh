#!/bin/bash
# benchmark/scripts/test_make_variants.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
gzip -c "$ROOT/testdata/R1.fq" > "$T/ds_R1.fastq.gz"

out=$(bash "$HERE/make_variants.sh" "$T/ds_R1.fastq.gz" "$T/v" 6 2)
[ "$(echo "$out" | wc -l | tr -d ' ')" = 2 ] || { echo "expected 2 output lines"; exit 1; }

plain="$T/v/ds_R1.plain.fastq.gz"; bgzf="$T/v/ds_R1.bgzf.fastq.gz"
[ -s "$plain" ] && [ -s "$bgzf" ] || { echo "variant files missing"; exit 1; }

# plain: gzip FLG byte (offset 3) has no FEXTRA, so it is not BGZF
[ "$(xxd -s 3 -l 1 -p "$plain")" = "00" ] || { echo "plain variant has header flags"; exit 1; }
# bgzf: FEXTRA set and subfield id 'BC' at offset 12
[ "$(xxd -s 12 -l 2 -p "$bgzf")" = "4243" ] || { echo "bgzf variant missing BC subfield"; exit 1; }
cmp <(gzip -dc "$plain") "$ROOT/testdata/R1.fq" || { echo "plain content differs"; exit 1; }
cmp <(gzip -dc "$bgzf") "$ROOT/testdata/R1.fq" || { echo "bgzf content differs"; exit 1; }

# second run must reuse files, not rewrite them
before=$(stat -f %m "$plain" 2>/dev/null || stat -c %Y "$plain")
sleep 1; bash "$HERE/make_variants.sh" "$T/ds_R1.fastq.gz" "$T/v" 6 2 >/dev/null
after=$(stat -f %m "$plain" 2>/dev/null || stat -c %Y "$plain")
[ "$before" = "$after" ] || { echo "existing variant was rewritten"; exit 1; }
echo PASS
