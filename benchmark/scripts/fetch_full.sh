#!/bin/bash
# Downloads complete ENA runs (not subsets) for full-size benchmarks.
# Usage: fetch_full.sh <data_dir> "<name>:<accession>:<PE|SE> ..."
# Writes <data_dir>/<name>_R1.fastq.gz (and _R2 for PE). Existing files are kept.
set -euo pipefail
D=${1:?usage: fetch_full.sh <data_dir> "<name:accession:layout ...>"}; SPECS=${2:?}
mkdir -p "$D"
for spec in $SPECS; do
  IFS=: read -r name acc layout <<< "$spec"
  for u in $(curl -sf "https://www.ebi.ac.uk/ena/portal/api/filereport?accession=$acc&result=read_run&fields=fastq_ftp" | tail -1 | cut -f2 | tr ';' '\n'); do
    case $u in
      *_1.fastq.gz) m=1 ;;
      *_2.fastq.gz) m=2 ;;
      *) [ "$layout" = SE ] && m=1 || continue ;;
    esac
    dest="$D/${name}_R$m.fastq.gz"
    if [ ! -s "$dest" ]; then curl -sf --retry 20 --retry-all-errors -C - -o "$dest.part" "https://$u"; mv "$dest.part" "$dest"; fi
  done
done
ls -la "$D"
