# Codec / I/O decomposition

Source: `io.tsv`, `codec.tsv`


## atac_hiseq, -w 16

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 200.2 | 199.1 | 2598 | 13.0 | 1.94 | fp-read-L: 92%, fp-read-R: 86%, fp-work-0: 74% |
| gz_gz_z1 | 195.4 | 194.3 | 2288 | 11.7 | 1.99 | fp-read-L: 95%, fp-read-R: 87%, fp-work-5: 64% |
| gz_plain | 200.3 | 199.2 | 2093 | 10.4 | 1.94 | fp-read-L: 95%, fp-read-R: 94%, fp-work-0: 55% |
| gz_none | 201.7 | 200.6 | 2002 | 9.9 | 1.92 | fp-read-L: 97%, fp-read-R: 92%, fp-work-7: 53% |
| plain_gz | 167.6 | 166.7 | 2526 | 15.1 | 2.31 | fp-read-L: 97%, fp-read-R: 89%, fp-work-4: 85% |
| plain_plain | 176.9 | 176.0 | 2022 | 11.4 | 2.19 | fp-read-L: 99%, fp-read-R: 81%, fp-work-4: 60% |
| plain_none | 185.2 | 184.2 | 1973 | 10.7 | 2.09 | fp-read-R: 99%, fp-read-L: 82%, fp-work-0: 57% |
| bgzf_gz | 194.6 | 193.6 | 2925 | 15.0 | 1.99 | fp-read-L: 85%, fp-read-R: 84%, fp-work-0: 79% |
| bgzf_plain | 195.1 | 194.0 | 2414 | 12.4 | 1.99 | fp-read-R: 94%, fp-read-L: 82%, fp-work-0: 60% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 32.6 | 71 | 3% |
| output compression (gz_gz − gz_plain) | -0.2 | 505 | 19% |
| output write (gz_plain − gz_none) | -1.4 | 91 | 4% |
| both codecs (gz_gz − plain_plain) | 23.2 | 575 | 22% |
| BGZF input (gz_gz − bgzf_gz) | 5.6 | -328 | -13% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | 4.8 | 309 | 12% |
| compute floor: plain_none CPU | – | 1973 | 76% |

Reader ceiling (largest mate 32.6 GB ÷ igzip 690 MB/s, one thread): **47.2 s** vs gz_gz processing 199.1 s → 24% of processing time is the minimum a single-threaded inflate needs.

## atac_hiseq, -w 48

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 270.3 | 269.1 | 3473 | 12.8 | 1.43 | fp-read-R: 97%, fp-read-L: 95%, fp-work-15: 23% |
| gz_gz_z1 | 264.1 | 262.9 | 3023 | 11.4 | 1.47 | fp-read-L: 98%, fp-read-R: 91%, fp-work-23: 20% |
| gz_plain | 273.6 | 272.3 | 2806 | 10.3 | 1.42 | fp-read-L: 98%, fp-read-R: 90%, fp-work-23: 17% |
| gz_none | 268.3 | 267.1 | 2705 | 10.1 | 1.44 | fp-read-L: 97%, fp-read-R: 96%, fp-work-1: 18% |
| plain_gz | 233.8 | 232.7 | 3343 | 14.3 | 1.66 | fp-read-L: 97%, fp-read-R: 93%, fp-work-19: 26% |
| plain_plain | 235.3 | 234.2 | 2657 | 11.3 | 1.65 | fp-read-L: 98%, fp-read-R: 92%, fp-work-0: 20% |
| plain_none | 236.4 | 235.3 | 2605 | 11.0 | 1.64 | fp-read-L: 96%, fp-read-R: 95%, fp-work-16: 20% |
| bgzf_gz | 270.3 | 269.1 | 3489 | 12.9 | 1.43 | fp-read-R: 84%, fp-read-L: 83%, fp-work-29: 23% |
| bgzf_plain | 271.4 | 270.3 | 2817 | 10.4 | 1.43 | fp-read-R: 86%, fp-read-L: 83%, fp-work-0: 17% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 36.5 | 129 | 4% |
| output compression (gz_gz − gz_plain) | -3.2 | 666 | 19% |
| output write (gz_plain − gz_none) | 5.2 | 101 | 3% |
| both codecs (gz_gz − plain_plain) | 35.0 | 816 | 23% |
| BGZF input (gz_gz − bgzf_gz) | 0.0 | -16 | -0% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | 6.2 | 450 | 13% |
| compute floor: plain_none CPU | – | 2605 | 75% |

Reader ceiling (largest mate 32.6 GB ÷ igzip 690 MB/s, one thread): **47.2 s** vs gz_gz processing 269.1 s → 18% of processing time is the minimum a single-threaded inflate needs.

## rna_nova, -w 16

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 62.3 | 55.3 | 862 | 13.8 | 1.12 | fp-work-5: 92%, fp-work-7: 91%, fp-work-14: 91% |
| gz_gz_z1 | 56.8 | 49.8 | 766 | 13.5 | 1.25 | fp-work-3: 88%, fp-work-8: 88%, fp-work-4: 88% |
| gz_plain | 53.1 | 46.1 | 704 | 13.2 | 1.35 | fp-work-7: 86%, fp-work-5: 86%, fp-work-0: 85% |
| gz_none | 52.0 | 44.9 | 683 | 13.1 | 1.38 | fp-work-1: 86%, fp-work-10: 86%, fp-work-5: 86% |
| plain_gz | 58.0 | 51.1 | 829 | 14.3 | 1.21 | fp-work-1: 97%, fp-work-5: 96%, fp-work-7: 94% |
| plain_plain | 47.2 | 40.4 | 673 | 14.2 | 1.54 | fp-work-4: 95%, fp-work-0: 94%, fp-work-1: 94% |
| plain_none | 46.2 | 39.3 | 655 | 14.2 | 1.58 | fp-work-0: 99%, fp-work-4: 95%, fp-work-11: 95% |
| bgzf_gz | 67.7 | 60.6 | 997 | 14.7 | 1.02 | fp-work-10: 88%, fp-work-4: 88%, fp-work-9: 88% |
| bgzf_plain | 55.9 | 48.9 | 855 | 15.3 | 1.27 | fp-work-13: 91%, fp-work-0: 90%, fp-work-3: 89% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 4.3 | 33 | 4% |
| output compression (gz_gz − gz_plain) | 9.1 | 158 | 18% |
| output write (gz_plain − gz_none) | 1.2 | 21 | 2% |
| both codecs (gz_gz − plain_plain) | 15.0 | 189 | 22% |
| BGZF input (gz_gz − bgzf_gz) | -5.4 | -135 | -16% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | 5.5 | 96 | 11% |
| compute floor: plain_none CPU | – | 655 | 76% |

Reader ceiling (largest mate 10.4 GB ÷ igzip 808 MB/s, one thread): **12.9 s** vs gz_gz processing 55.3 s → 23% of processing time is the minimum a single-threaded inflate needs.

## rna_nova, -w 48

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 59.0 | 51.8 | 1240 | 21.0 | 1.20 | fp-read-L: 98%, fp-read-R: 95%, fp-work-38: 48% |
| gz_gz_z1 | 57.1 | 49.9 | 1104 | 19.3 | 1.24 | fp-read-R: 96%, fp-read-L: 96%, fp-work-6: 44% |
| gz_plain | 58.5 | 51.2 | 962 | 16.5 | 1.21 | fp-read-R: 97%, fp-read-L: 96%, fp-work-3: 36% |
| gz_none | 56.3 | 49.1 | 936 | 16.6 | 1.26 | fp-read-R: 98%, fp-read-L: 96%, fp-work-18: 38% |
| plain_gz | 50.0 | 43.0 | 1232 | 24.7 | 1.44 | fp-read-L: 93%, fp-read-R: 92%, fp-work-2: 57% |
| plain_plain | 49.3 | 42.3 | 957 | 19.4 | 1.47 | fp-read-L: 96%, fp-read-R: 92%, fp-work-0: 44% |
| plain_none | 48.8 | 41.9 | 946 | 19.4 | 1.48 | fp-read-L: 96%, fp-read-R: 95%, fp-work-34: 46% |
| bgzf_gz | 62.0 | 54.8 | 1241 | 20.0 | 1.13 | fp-read-L: 76%, fp-read-R: 75%, fp-work-2: 44% |
| bgzf_plain | 61.2 | 54.0 | 989 | 16.2 | 1.15 | fp-read-R: 77%, fp-read-L: 76%, fp-work-0: 35% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 9.0 | 8 | 1% |
| output compression (gz_gz − gz_plain) | 0.5 | 278 | 22% |
| output write (gz_plain − gz_none) | 2.2 | 27 | 2% |
| both codecs (gz_gz − plain_plain) | 9.7 | 283 | 23% |
| BGZF input (gz_gz − bgzf_gz) | -3.0 | -1 | -0% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | 1.9 | 137 | 11% |
| compute floor: plain_none CPU | – | 946 | 76% |

Reader ceiling (largest mate 10.4 GB ÷ igzip 808 MB/s, one thread): **12.9 s** vs gz_gz processing 51.8 s → 25% of processing time is the minimum a single-threaded inflate needs.

## rna_se, -w 16

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 42.9 | 41.4 | 369 | 8.6 | 1.03 | fp-read: 99%, fp-work-4: 51%, fp-work-6: 51% |
| gz_gz_z1 | 44.4 | 42.9 | 332 | 7.5 | 0.99 | fp-read: 98%, fp-work-0: 46%, fp-work-2: 46% |
| gz_plain | 42.4 | 40.9 | 302 | 7.1 | 1.04 | fp-read: 98%, fp-work-14: 41%, fp-work-6: 41% |
| gz_none | 42.0 | 40.5 | 289 | 6.9 | 1.05 | fp-read: 99%, fp-work-6: 43%, fp-work-4: 41% |
| plain_gz | 35.3 | 33.9 | 349 | 9.9 | 1.26 | fp-read: 98%, fp-work-4: 60%, fp-work-1: 60% |
| plain_plain | 37.0 | 35.5 | 286 | 7.7 | 1.20 | fp-read: 99%, fp-work-11: 47%, fp-work-2: 46% |
| plain_none | 34.9 | 33.4 | 280 | 8.0 | 1.28 | fp-read: 99%, fp-work-2: 48%, fp-work-4: 48% |
| bgzf_gz | 45.0 | 43.5 | 456 | 10.1 | 0.98 | fp-read: 83%, fp-work-14: 53%, fp-work-15: 53% |
| bgzf_plain | 46.1 | 44.5 | 375 | 8.1 | 0.96 | fp-read: 85%, fp-work-1: 40%, fp-work-3: 38% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 7.5 | 20 | 5% |
| output compression (gz_gz − gz_plain) | 0.4 | 66 | 18% |
| output write (gz_plain − gz_none) | 0.5 | 14 | 4% |
| both codecs (gz_gz − plain_plain) | 5.9 | 83 | 22% |
| BGZF input (gz_gz − bgzf_gz) | -2.1 | -87 | -24% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | -1.5 | 37 | 10% |
| compute floor: plain_none CPU | – | 280 | 76% |

Reader ceiling (largest mate 9.3 GB ÷ igzip 766 MB/s, one thread): **12.1 s** vs gz_gz processing 41.4 s → 29% of processing time is the minimum a single-threaded inflate needs.

## rna_se, -w 48

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 53.9 | 52.4 | 457 | 8.5 | 0.81 | fp-read: 98%, fp-work-20: 17%, fp-work-24: 17% |
| gz_gz_z1 | 54.1 | 52.5 | 412 | 7.6 | 0.81 | fp-read: 98%, fp-work-20: 16%, fp-work-9: 15% |
| gz_plain | 54.3 | 52.8 | 377 | 6.9 | 0.81 | fp-read: 99%, fp-work-16: 13%, fp-work-23: 13% |
| gz_none | 53.3 | 51.7 | 367 | 6.9 | 0.82 | fp-read: 98%, fp-work-17: 13%, fp-work-15: 13% |
| plain_gz | 46.2 | 44.7 | 443 | 9.6 | 0.95 | fp-read: 98%, fp-work-22: 20%, fp-work-25: 19% |
| plain_plain | 46.0 | 44.5 | 362 | 7.9 | 0.96 | fp-read: 97%, fp-work-39: 15%, fp-work-0: 15% |
| plain_none | 45.8 | 44.3 | 364 | 7.9 | 0.96 | fp-read: 98%, fp-work-17: 16%, fp-work-20: 16% |
| bgzf_gz | 57.3 | 55.7 | 469 | 8.2 | 0.76 | fp-read: 84%, fp-bgzf: 21%, fp-work-23: 16% |
| bgzf_plain | 56.8 | 55.2 | 387 | 6.8 | 0.77 | fp-read: 84%, fp-bgzf: 21%, fp-work-21: 13% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 7.7 | 14 | 3% |
| output compression (gz_gz − gz_plain) | -0.4 | 79 | 17% |
| output write (gz_plain − gz_none) | 1.0 | 10 | 2% |
| both codecs (gz_gz − plain_plain) | 7.9 | 95 | 21% |
| BGZF input (gz_gz − bgzf_gz) | -3.4 | -13 | -3% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | -0.2 | 45 | 10% |
| compute floor: plain_none CPU | – | 364 | 80% |

Reader ceiling (largest mate 9.3 GB ÷ igzip 766 MB/s, one thread): **12.1 s** vs gz_gz processing 52.4 s → 23% of processing time is the minimum a single-threaded inflate needs.

## wgbs, -w 16

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 70.7 | 41.4 | 598 | 8.5 | 1.37 | fp-read-R: 90%, fp-work-0: 78%, fp-work-3: 78% |
| gz_gz_z1 | 68.4 | 39.1 | 518 | 7.6 | 1.45 | fp-read-R: 98%, fastp: 44%, fp-read-L: 72% |
| gz_plain | 66.6 | 37.6 | 448 | 6.7 | 1.51 | fp-read-R: 99%, fastp: 44%, fp-read-L: 68% |
| gz_none | 64.7 | 36.0 | 432 | 6.7 | 1.58 | fp-read-R: 99%, fastp: 45%, fp-read-L: 78% |
| plain_gz | 61.0 | 32.5 | 569 | 9.3 | 1.75 | fp-work-1: 96%, fp-work-4: 96%, fp-work-6: 95% |
| plain_plain | 57.0 | 28.3 | 436 | 7.6 | 2.00 | fastp: 50%, fp-read-R: 99%, fp-read-L: 92% |
| plain_none | 57.7 | 28.6 | 417 | 7.2 | 1.99 | fastp: 52%, fp-read-R: 99%, fp-read-L: 95% |
| bgzf_gz | 70.2 | 40.9 | 692 | 9.9 | 1.39 | fp-work-0: 85%, fp-work-2: 85%, fp-work-5: 84% |
| bgzf_plain | 65.8 | 36.6 | 558 | 8.5 | 1.55 | fp-read-R: 88%, fastp: 45%, fp-read-L: 72% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 9.7 | 28 | 5% |
| output compression (gz_gz − gz_plain) | 4.1 | 150 | 25% |
| output write (gz_plain − gz_none) | 2.0 | 15 | 3% |
| both codecs (gz_gz − plain_plain) | 13.7 | 162 | 27% |
| BGZF input (gz_gz − bgzf_gz) | 0.5 | -94 | -16% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | 2.3 | 80 | 13% |
| compute floor: plain_none CPU | – | 417 | 70% |

Reader ceiling (largest mate 7.0 GB ÷ igzip 847 MB/s, one thread): **8.2 s** vs gz_gz processing 41.4 s → 20% of processing time is the minimum a single-threaded inflate needs.

## wgbs, -w 48

| variant | wall s | process s | CPU s | CPU/wall | reads/s (M) | busiest threads (name: busy) |
|---|---|---|---|---|---|---|
| gz_gz | 78.0 | 49.0 | 763 | 9.8 | 1.16 | fp-read-R: 98%, fp-read-L: 73%, fastp: 38% |
| gz_gz_z1 | 77.8 | 48.0 | 664 | 8.5 | 1.18 | fp-read-R: 99%, fp-read-L: 76%, fastp: 39% |
| gz_plain | 76.0 | 47.0 | 571 | 7.5 | 1.21 | fp-read-R: 98%, fp-read-L: 78%, fastp: 39% |
| gz_none | 74.1 | 45.2 | 556 | 7.5 | 1.25 | fp-read-R: 98%, fp-read-L: 79%, fastp: 40% |
| plain_gz | 69.4 | 40.2 | 785 | 11.3 | 1.41 | fp-read-R: 97%, fp-read-L: 88%, fastp: 43% |
| plain_plain | 69.1 | 39.5 | 585 | 8.5 | 1.44 | fp-read-R: 97%, fp-read-L: 94%, fastp: 44% |
| plain_none | 68.9 | 39.6 | 565 | 8.2 | 1.43 | fp-read-R: 98%, fp-read-L: 89%, fastp: 43% |
| bgzf_gz | 83.0 | 52.2 | 800 | 9.6 | 1.09 | fp-read-R: 76%, fp-read-L: 64%, fastp: 38% |
| bgzf_plain | 80.9 | 51.2 | 605 | 7.5 | 1.11 | fp-read-R: 77%, fp-read-L: 63%, fastp: 37% |

| stage (difference) | wall saved s | CPU saved s | share of gz_gz CPU |
|---|---|---|---|
| input decompression (gz_gz − plain_gz) | 8.6 | -22 | -3% |
| output compression (gz_gz − gz_plain) | 1.9 | 191 | 25% |
| output write (gz_plain − gz_none) | 1.9 | 15 | 2% |
| both codecs (gz_gz − plain_plain) | 8.9 | 178 | 23% |
| BGZF input (gz_gz − bgzf_gz) | -5.1 | -37 | -5% |
| -z 4 → -z 1 (gz_gz − gz_gz_z1) | 0.2 | 99 | 13% |
| compute floor: plain_none CPU | – | 565 | 74% |

Reader ceiling (largest mate 7.0 GB ÷ igzip 847 MB/s, one thread): **8.2 s** vs gz_gz processing 49.0 s → 17% of processing time is the minimum a single-threaded inflate needs.

## Standalone codec throughput (page cache → /dev/null)

| dataset | tool | op | threads | level | wall s | MB/s (uncompressed) | MB/s per CPU-core |
|---|---|---|---|---|---|---|---|
| rna_nova | igzip | decompress | 1 | - | 12.92 | 808 | 893 |
| rna_nova | pigz | decompress | 1 | - | 21.62 | 483 | 335 |
| rna_nova | libdeflate | decompress | 1 | - | 33.84 | 308 | 319 |
| rna_nova | rapidgzip | decompress | 1 | - | 13.55 | 770 | 840 |
| rna_nova | rapidgzip | decompress | 4 | - | 12.67 | 824 | 225 |
| rna_nova | rapidgzip | decompress | 16 | - | 4.52 | 2309 | 223 |
| rna_nova | rapidgzip | decompress | 48 | - | 5.19 | 2011 | 160 |
| rna_nova | libdeflate | compress | 1 | 1 | 40.66 | 257 | 259 |
| rna_nova | libdeflate | compress | 1 | 4 | 83.66 | 125 | 125 |
| rna_nova | libdeflate | compress | 1 | 6 | 163.61 | 64 | 64 |
| rna_nova | igzip | compress | 1 | 1 | 22.70 | 460 | 467 |
| rna_nova | pigz | compress | 1 | 4 | 138.13 | 76 | 76 |
| rna_nova | pigz | compress | 4 | 4 | 34.67 | 301 | 71 |
| rna_nova | pigz | compress | 16 | 4 | 8.69 | 1201 | 71 |
| rna_nova | pigz | compress | 48 | 4 | 14.44 | 723 | 43 |
| rna_nova | bgzip | compress | 1 | 4 | 108.41 | 96 | 96 |
| rna_nova | bgzip | compress | 4 | 4 | 26.87 | 388 | 92 |
| rna_nova | bgzip | compress | 16 | 4 | 6.97 | 1498 | 89 |
| rna_nova | bgzip | compress | 48 | 4 | 4.93 | 2117 | 71 |
| rna_nova | bgzip | decompress | 1 | - | 12.55 | 832 | 832 |
| rna_nova | bgzip | decompress | 4 | - | 3.99 | 2616 | 536 |
| rna_nova | bgzip | decompress | 16 | - | 4.17 | 2503 | 511 |
| rna_nova | bgzip | decompress | 48 | - | 4.44 | 2351 | 532 |
| rna_nova | igzip | decompress-bgzf | 1 | - | 14.98 | 697 | 697 |
| wgbs | igzip | decompress | 1 | - | 8.21 | 847 | 953 |
| wgbs | pigz | decompress | 1 | - | 15.15 | 459 | 318 |
| wgbs | libdeflate | decompress | 1 | - | 20.53 | 339 | 351 |
| wgbs | rapidgzip | decompress | 1 | - | 8.87 | 784 | 867 |
| wgbs | rapidgzip | decompress | 4 | - | 8.41 | 827 | 233 |
| wgbs | rapidgzip | decompress | 16 | - | 3.16 | 2201 | 223 |
| wgbs | rapidgzip | decompress | 48 | - | 3.60 | 1932 | 163 |
| wgbs | libdeflate | compress | 1 | 1 | 26.32 | 264 | 266 |
| wgbs | libdeflate | compress | 1 | 4 | 50.86 | 137 | 137 |
| wgbs | libdeflate | compress | 1 | 6 | 91.94 | 76 | 76 |
| wgbs | igzip | compress | 1 | 1 | 14.86 | 468 | 474 |
| wgbs | pigz | compress | 1 | 4 | 91.16 | 76 | 76 |
| wgbs | pigz | compress | 4 | 4 | 22.96 | 303 | 72 |
| wgbs | pigz | compress | 16 | 4 | 5.84 | 1191 | 71 |
| wgbs | pigz | compress | 48 | 4 | 9.82 | 708 | 44 |
| wgbs | bgzip | compress | 1 | 4 | 61.83 | 112 | 113 |
| wgbs | bgzip | compress | 4 | 4 | 15.63 | 445 | 106 |
| wgbs | bgzip | compress | 16 | 4 | 4.11 | 1692 | 101 |
| wgbs | bgzip | compress | 48 | 4 | 2.86 | 2432 | 81 |
| wgbs | bgzip | decompress | 1 | - | 7.75 | 898 | 900 |
| wgbs | bgzip | decompress | 4 | - | 2.59 | 2686 | 663 |
| wgbs | bgzip | decompress | 16 | - | 2.83 | 2458 | 567 |
| wgbs | bgzip | decompress | 48 | - | 2.70 | 2576 | 577 |
| wgbs | igzip | decompress-bgzf | 1 | - | 8.11 | 858 | 858 |
| atac_hiseq | igzip | decompress | 1 | - | 47.22 | 690 | 758 |
| atac_hiseq | pigz | decompress | 1 | - | 92.52 | 352 | 262 |
| atac_hiseq | libdeflate | decompress | 1 | - | 120.06 | 271 | 280 |
| atac_hiseq | rapidgzip | decompress | 1 | - | 49.12 | 663 | 721 |
| atac_hiseq | rapidgzip | decompress | 4 | - | 43.14 | 755 | 199 |
| atac_hiseq | rapidgzip | decompress | 16 | - | 14.98 | 2175 | 200 |
| atac_hiseq | rapidgzip | decompress | 48 | - | 14.54 | 2241 | 158 |
| atac_hiseq | libdeflate | compress | 1 | 1 | 135.08 | 241 | 244 |
| atac_hiseq | libdeflate | compress | 1 | 4 | 310.86 | 105 | 105 |
| atac_hiseq | libdeflate | compress | 1 | 6 | 586.20 | 56 | 56 |
| atac_hiseq | igzip | compress | 1 | 1 | 85.56 | 381 | 388 |
| atac_hiseq | pigz | compress | 1 | 4 | 508.33 | 64 | 64 |
| atac_hiseq | pigz | compress | 4 | 4 | 129.12 | 252 | 60 |
| atac_hiseq | pigz | compress | 16 | 4 | 32.11 | 1015 | 60 |
| atac_hiseq | pigz | compress | 48 | 4 | 46.08 | 707 | 38 |
| atac_hiseq | bgzip | compress | 1 | 4 | 388.54 | 84 | 84 |
| atac_hiseq | bgzip | compress | 4 | 4 | 96.74 | 337 | 81 |
| atac_hiseq | bgzip | compress | 16 | 4 | 24.68 | 1320 | 79 |
| atac_hiseq | bgzip | compress | 48 | 4 | 15.17 | 2148 | 60 |
| atac_hiseq | bgzip | decompress | 1 | - | 47.28 | 689 | 689 |
| atac_hiseq | bgzip | decompress | 4 | - | 13.16 | 2476 | 531 |
| atac_hiseq | bgzip | decompress | 16 | - | 13.01 | 2505 | 503 |
| atac_hiseq | bgzip | decompress | 48 | - | 13.57 | 2401 | 485 |
| atac_hiseq | igzip | decompress-bgzf | 1 | - | 49.93 | 653 | 653 |
| rna_se | igzip | decompress | 1 | - | 12.13 | 766 | 857 |
| rna_se | pigz | decompress | 1 | - | 20.90 | 444 | 307 |
| rna_se | libdeflate | decompress | 1 | - | 29.02 | 320 | 333 |
| rna_se | rapidgzip | decompress | 1 | - | 12.51 | 742 | 817 |
| rna_se | rapidgzip | decompress | 4 | - | 11.37 | 817 | 225 |
| rna_se | rapidgzip | decompress | 16 | - | 4.10 | 2265 | 216 |
| rna_se | rapidgzip | decompress | 48 | - | 4.84 | 1919 | 159 |
| rna_se | libdeflate | compress | 1 | 1 | 34.72 | 267 | 270 |
| rna_se | libdeflate | compress | 1 | 4 | 73.41 | 126 | 127 |
| rna_se | libdeflate | compress | 1 | 6 | 141.76 | 66 | 66 |
| rna_se | igzip | compress | 1 | 1 | 20.49 | 453 | 462 |
| rna_se | pigz | compress | 1 | 4 | 120.36 | 77 | 77 |
| rna_se | pigz | compress | 4 | 4 | 30.44 | 305 | 72 |
| rna_se | pigz | compress | 16 | 4 | 7.63 | 1217 | 72 |
| rna_se | pigz | compress | 48 | 4 | 13.25 | 701 | 44 |
| rna_se | bgzip | compress | 1 | 4 | 92.80 | 100 | 100 |
| rna_se | bgzip | compress | 4 | 4 | 23.11 | 402 | 95 |
| rna_se | bgzip | compress | 16 | 4 | 5.98 | 1553 | 93 |
| rna_se | bgzip | compress | 48 | 4 | 4.16 | 2232 | 77 |
| rna_se | bgzip | decompress | 1 | - | 11.30 | 822 | 822 |
| rna_se | bgzip | decompress | 4 | - | 3.73 | 2490 | 559 |
| rna_se | bgzip | decompress | 16 | - | 3.81 | 2437 | 577 |
| rna_se | bgzip | decompress | 48 | - | 4.14 | 2243 | 570 |
| rna_se | igzip | decompress-bgzf | 1 | - | 12.43 | 747 | 748 |
