#!/bin/bash
# Builds the two inputs the gzip-vs-BGZF benchmark compares, from the SAME reads at the SAME
# compression level: plain gzip (`gzip -L`) and BGZF (`bgzip -l L`). The corpus from
# fetch_corpus.sh is gzip -1, so it is not used directly.
# Usage: make_variants.sh <in.fastq.gz> <out_dir> [level=6] [threads=4]
# Prints "<variant>\t<bytes>\t<level>" per variant.
# No `set -e`: every step is checked explicitly so failures name the step.
set -uo pipefail
IN=${1:?usage: make_variants.sh <in.fastq.gz> <out_dir> [level] [threads]}
OUT=${2:?}
LEVEL=${3:-6}
THREADS=${4:-4}
command -v bgzip >/dev/null || { echo "bgzip not found (install htslib)" >&2; exit 1; }
[ -s "$IN" ] || { echo "input missing or empty: $IN" >&2; exit 1; }
mkdir -p "$OUT" || { echo "cannot create output dir: $OUT" >&2; exit 1; }
base=$(basename "$IN" .fastq.gz)
plain="$OUT/$base.plain.fastq.gz"
bgzf="$OUT/$base.bgzf.fastq.gz"

# Write to .tmp then rename, so an interrupted run never leaves a truncated "complete" file.
if [ ! -s "$plain" ]; then
  if ! { gzip -dc "$IN" | gzip -"$LEVEL" > "$plain.tmp"; } || ! mv "$plain.tmp" "$plain"; then
    echo "plain build failed for $IN" >&2; rm -f "$plain.tmp"; exit 1
  fi
fi
if [ ! -s "$bgzf" ]; then
  if ! { gzip -dc "$IN" | bgzip -@ "$THREADS" -l "$LEVEL" > "$bgzf.tmp"; } || ! mv "$bgzf.tmp" "$bgzf"; then
    echo "BGZF build failed for $IN" >&2; rm -f "$bgzf.tmp"; exit 1
  fi
fi

# Both variants must decode to identical bytes (compare digests, not files, so a 40 GB stream is not held).
if command -v md5sum >/dev/null; then H=md5sum; else H="md5 -q"; fi
a=$(gzip -dc "$plain" | $H) || { echo "cannot decode plain variant: $plain" >&2; exit 1; }
b=$(gzip -dc "$bgzf" | $H) || { echo "cannot decode BGZF variant: $bgzf" >&2; exit 1; }
[ -n "$a" ] && [ -n "$b" ] || { echo "empty digest for $IN" >&2; exit 1; }
[ "$a" = "$b" ] || { echo "variant contents differ for $IN" >&2; exit 1; }

printf 'plain\t%s\t%s\n' "$(wc -c < "$plain" | tr -d ' ')" "$LEVEL"
printf 'bgzf\t%s\t%s\n' "$(wc -c < "$bgzf" | tr -d ' ')" "$LEVEL"
