"""Projects CPU time, GPU time, wall time and (optionally) cost per sample for each way of
reformulating fastp, from measured per-read costs. Nothing here is a benchmark itself; every
input is a measurement from another script, and the formulas are printed with the results.

Inputs (JSON):
  --trace   trace_analyze.py --json for the normal run (gz in, gz out) on the CPU box
  --soa     soa_pack output on the same CPU box (index/pack/emit/kernel ns per read, bytes)
  --gpu     gpu_bench.py --json on the GPU box (PCIe, kernel, nvCOMP rates)   [optional]
  --prep    io_variants.sh prep.tsv (cost of making BGZF input)             [optional]
  --codec   codec_baselines.sh TSV (rapidgzip scaling)                      [optional]
Sample and machine:
  --gz-bytes B (compressed input size, all mates; default: estimated from fastp's output ratio)
  --bgzf-input (for B: input is BGZF, use batched block inflate instead of single-stream)
  --dataset NAME (select this dataset's rows in --prep / --codec)
  --reads N (per mate; default: the traced run's)   --workers W (default 16)   --vcpus V (default 48)
  --cpu-price $/h   --gpu-price $/h   (both optional; without them only times are reported)
  --qc-speedups 5,20  extra rows for A/B/C with fastp's per-read QC sped up by these factors
                      instead of the analogue kernel's measured CPU/GPU ratio (sensitivity)

Reformulations (see reformulations.md for when each is useful):
  base   fastp as-is
  D1     BGZF input (fastp's parallel BGZF reader), paying the one-off conversion if the
         sequencer's output is ordinary gzip
  D2     parallel decompression of ordinary gzip in the reader (rapidgzip-style)
  D3     -z 1 output
  D4     uncompressed output streamed into the next tool (no compress here, no inflate there)
  A      offload per-read QC to a GPU; CPU keeps inflate, parse (into SoA), serialise, compress
  B      GPU-resident: GPU inflates, parses, QCs and compresses; CPU only moves bytes
  C      fused into a GPU aligner: QC runs on reads the aligner already holds on the GPU; the
         trimmed .fastq.gz is never written or re-read
"""
import csv, json, sys


def opt(name, default=None, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def load(name):
    p = opt(name)
    return json.load(open(p)) if p else None


tr, soa, gpu = load('--trace'), load('--soa'), load('--gpu')
if not tr or not soa:
    sys.exit(__doc__)
mates = tr['mates']
reads = opt('--reads', tr['reads_per_mate'], int)          # per mate
R = reads * mates                                            # all reads
W = opt('--workers', 16, int)
V = opt('--vcpus', 48, int)
cpu_price, gpu_price = opt('--cpu-price', None, float), opt('--gpu-price', None, float)
DS = opt('--dataset')
if DS is None and (opt('--prep') or opt('--codec')):
    print('warning: no --dataset; --prep/--codec rows from every dataset are combined', file=sys.stderr)


def tsv(name):
    rows = list(csv.DictReader(open(opt(name)), delimiter='\t')) if opt(name) else []
    key = 'step' if name == '--prep' else 'dataset'
    return [r for r in rows if DS is None or r[key] == DS or r[key].startswith(DS + '.')]

# measured per-read CPU ns (trace)
d, p, w, c, wr = (tr[k] for k in ('decompress_ns_per_read', 'parse_ns_per_read', 'process_ns_per_read',
                                  'compress_ns_per_read', 'write_ns_per_read'))
ratio = tr['compress_in_bytes'] / max(tr['compress_out_bytes'], 1)
text_b = soa['bytes_per_read']['fastq_text']                 # uncompressed bytes per read
# compressed input bytes per read: pass --gz-bytes (input .gz size, all mates) or assume fastp's output ratio
gz_in_b = opt('--gz-bytes', None, float) / R if opt('--gz-bytes') else text_b / ratio
S = soa['ns_per_read']
kept_text_b = text_b * soa['kept'] / soa['reads']

rows, notes = [], []


def row(name, cpu_ns, gpu_ns, wall_s, transform_cpu_ns=0.0, extra=''):
    """cpu_ns / gpu_ns: per read (all mates); wall_s: whole sample."""
    cpu_s, gpu_s = cpu_ns * R / 1e9, gpu_ns * R / 1e9
    cost = None
    if cpu_price is not None:
        # CPU box billed for the wall time; a GPU box too when the GPU is used
        cost = wall_s / 3600 * (cpu_price + (gpu_price or 0) * (gpu_ns > 0))
    rows.append((name, cpu_s, transform_cpu_ns * R / 1e9, gpu_s, wall_s, cost, extra))


# ---- base: two pipeline stages; wall = the slower
reader_wall = reads * (d + p) / 1e9                           # one thread per mate, mates in parallel
worker_wall = R * (w + c + wr) / 1e9 / W
base_wall = max(reader_wall, worker_wall)
row('base', d + p + w + c + wr, 0, base_wall,
    extra=f'reader {reader_wall:.0f}s vs workers {worker_wall:.0f}s')

# ---- D1: BGZF input. Reader keeps parse; inflate moves to a pool of (V - W - 4)/mates threads
# fastp: PE budget (nproc - (w + 4)) / gz inputs (peprocessor.cpp), SE (nproc - w - 3) (seprocessor.cpp)
pool = max(1, (V - (W + 4)) // mates) if mates == 2 else max(1, V - W - 3)
d1_reader = reads * (p + d / pool) / 1e9
conv_ns = 0.0
if opt('--prep'):
    for r in tsv('--prep'):
        if 'bgzip' in r['step'] or 'gunzip' in r['step']:
            conv_ns += (float(r['user']) + float(r['sys'])) * 1e9
    conv_ns /= max(tr['reads_total'], 1)  # prep was measured on the traced dataset
row('D1 BGZF input', d + p + w + c + wr, 0, max(d1_reader, worker_wall), conv_ns,
    f'pool {pool} thr/mate; transform = gunzip + bgzip once, only if input isn\'t BGZF already')

# ---- D2: parallel inflate of ordinary gzip (rapidgzip-style): same pool, ~same CPU/byte + overhead
rg_over = 1.0
if opt('--codec'):
    one = {r['threads']: r for r in tsv('--codec') if r['tool'] == 'rapidgzip' and r['op'] == 'decompress'}
    ig = [r for r in tsv('--codec') if r['tool'] == 'igzip' and r['op'] == 'decompress']
    if one and ig:
        best = max(one.values(), key=lambda r: int(r['threads']))
        rg_over = float(ig[0]['cpu_MBps_per_core']) / max(float(best['cpu_MBps_per_core']), 1)
row('D2 parallel gzip reader', d * rg_over + p + w + c + wr, 0, max(reads * (p + d * rg_over / pool) / 1e9, worker_wall),
    extra=f'CPU/byte x{rg_over:.2f} vs ISA-L (from codec baselines)')

# ---- D3: -z 1 (libdeflate level 1 ~ 2x faster than 4 per codec baselines; use measured if present)
z_speed = 2.0
if opt('--codec'):
    lv = {r['level']: float(r['cpu_MBps_per_core']) for r in tsv('--codec')
          if r['tool'] == 'libdeflate' and r['op'] == 'compress'}
    if '1' in lv and '4' in lv:
        z_speed = lv['1'] / lv['4']
row('D3 -z 1', d + p + w + c / z_speed + wr, 0, max(reader_wall, R * (w + c / z_speed + wr) / 1e9 / W),
    extra=f'compress x{z_speed:.1f} faster, output larger')

# ---- D4: stream uncompressed output straight into the next tool (--stdout / named pipe)
downstream_inflate = d * soa['kept'] / soa['reads']            # next tool no longer inflates trimmed reads
row('D4 uncompressed stream to aligner', d + p + w + wr, 0, max(reader_wall, R * (w + wr) / 1e9 / W),
    -downstream_inflate, 'no output compression; negative transform = downstream inflate avoided')

if gpu and 'kernel' in gpu:
    K = gpu['kernel']
    h2d = gpu['pcie']['256MB']['h2d_GBps'] * 1e9
    d2h = gpu['pcie']['256MB']['d2h_GBps'] * 1e9
    measured = S['kernel'] / K['kernel_ns_per_read']         # same kernel, CPU vs GPU
    # fastp's process = QC work + serialising output text; soa emit measures the latter
    qc_cpu = max(w - S['emit'], 0)
    extra_sp = [float(x) for x in opt('--qc-speedups', '').split(',') if x]
    scenarios = [(measured, f'{measured:.0f}x (measured kernel)')] + [(x, f'{x:.0f}x (assumed)') for x in extra_sp]
for speedup, sp_label in (scenarios if gpu and 'kernel' in gpu else []):
    qc_gpu = qc_cpu / speedup
    pcie_a = (soa['bytes_per_read']['soa_fixed'] / h2d + soa['bytes_per_read']['decisions'] / d2h) * 1e9
    # ---- A: CPU parses into SoA (index + pack instead of Read objects), GPU QCs, CPU emits+compresses
    a_cpu = d + S['index'] + S['pack'] + S['emit'] + c + wr
    a_reader = reads * (d + S['index'] + S['pack']) / 1e9
    a_worker = R * (S['emit'] + c + wr) / 1e9 / W
    a_gpu = qc_gpu + pcie_a
    row(f'A offload per-read QC, QC {sp_label}', a_cpu, a_gpu, max(a_reader, a_worker, R * a_gpu / 1e9),
        (S['index'] + S['pack'] - p),
        f'PCIe {pcie_a:.0f} ns/read; QC share of process {qc_cpu / w:.0%}')

    # ---- B: GPU-resident
    # ordinary sequencer .gz can only use the single-stream rate; the batched BGZF rate
    # applies only when the input really is BGZF (--bgzf-input)
    inflate, src = None, ''
    g1 = gpu.get('gzip1', {}).get('nvlzcat', {})
    if '--bgzf-input' in sys.argv:
        if gpu.get('bgzf', {}).get('GBps_uncompressed'):
            inflate = text_b / (gpu['bgzf']['GBps_uncompressed'] * 1e9) * 1e9; src = 'BGZF batched'
    elif isinstance(g1, dict) and g1.get('GBps_uncompressed'):
        inflate, src = text_b / (g1['GBps_uncompressed'] * 1e9) * 1e9, 'single-stream gzip (nvlzcat)'
    # output must stay .gz: raw Deflate chunks (framed as gzip members on the CPU, like BGZF) or
    # nvlzcat's gzip; GDeflate is not gzip-compatible. Take the fastest config whose ratio is
    # within 90% of fastp's libdeflate -z 4 ratio, else the best ratio available.
    cands = [(k, v) for k, v in (gpu.get('deflate') or {}).items()
             if isinstance(v, dict) and v.get('GBps_in') and v.get('ratio') and not k.startswith('GDeflate')]
    good = [kv for kv in cands if kv[1]['ratio'] >= 0.9 * ratio]
    pick = max(good, key=lambda kv: kv[1]['GBps_in']) if good else (max(cands, key=lambda kv: kv[1]['ratio']) if cands else None)
    comp, comp_ratio, comp_name = None, ratio, '-'
    if pick:
        comp_name, v = pick
        comp, comp_ratio = kept_text_b / (v['GBps_in'] * 1e9) * 1e9, v['ratio']
    if inflate is not None and comp is not None:
        parse_gpu = S['index'] / speedup                      # structural scan: assume it parallelises like the kernel
        b_gpu = inflate + parse_gpu + qc_gpu + comp
        pcie_b = (gz_in_b / h2d + kept_text_b / comp_ratio / d2h) * 1e9
        b_cpu = wr + 50                                        # file I/O + orchestration
        row(f'B GPU-resident, QC {sp_label}', b_cpu, b_gpu + pcie_b, R * max(b_gpu, pcie_b) / 1e9, 0,
            f'inflate: {src}; compress: {comp_name}, ratio {comp_ratio:.2f} vs libdeflate {ratio:.2f}')
    # ---- C: fused into GPU aligner
    c_gpu = qc_gpu + S['index'] / speedup
    saved_downstream = d * soa['kept'] / soa['reads']        # aligner no longer re-inflates trimmed reads
    row(f'C fused into GPU aligner, QC {sp_label}', 0, c_gpu, R * c_gpu / 1e9, -saved_downstream,
        'fastp CPU work disappears; negative transform = downstream re-read avoided')
if gpu and 'kernel' in gpu:
    notes += ['A/B/C: "measured kernel" applies the analogue kernel\'s CPU/GPU speedup to all of fastp\'s QC work '
              '(process minus output serialisation). fastp also does k-mer, duplication and overrepresentation stats '
              'and per-read string handling that may not speed up as much; the "assumed" rows bracket that.',
              'B: GPU parse cost is not measured (no GPU FASTQ parser exists); modelled as the CPU index scan '
              'divided by the speedup.',
              'C needs the aligner to expose a pre-alignment hook; Parabricks fq2bam does not (no trimming).']
else:
    notes.append('No --gpu JSON: GPU reformulations (A, B, C) not projected.')

print(f'# Reformulation projection\n')
print(f'Sample: {reads:,} reads per mate x {mates} mate(s); CPU box {V} vCPUs, fastp -w {W}.')
print(f'Measured per read (trace): decompress {d:.0f} ns, parse {p:.0f}, process {w:.0f}, compress {c:.0f}, '
      f'write {wr:.0f}. Transforms (soa_pack): index {S["index"]:.0f}, pack {S["pack"]:.0f}, emit {S["emit"]:.0f}, '
      f'CPU kernel {S["kernel"]:.0f}.\n')
hdr = '| reformulation | CPU s | one-off transform CPU s | GPU s | projected wall s | vs base | $ / sample | notes |'
print(hdr)
print('|---' * 8 + '|')
for name, cs, ts, gs, ws, cost, extra in rows:
    print(f'| {name} | {cs:.1f} | {ts:.1f} | {gs:.1f} | {ws:.1f} | {base_wall / ws:.2f}x | '
          f'{"-" if cost is None else f"{cost:.3f}"} | {extra} |')
print('\nWall is the slowest overlapped stage (reader, workers, GPU, PCIe) and ignores the fixed '
      'pre/detect stages from full-size.md. CPU s is summed across threads.')
for n in notes:
    print(f'- {n}')
