"""GPU side of the reformulation cost model: what each GPU step costs on real data.

  pcie     host<->device copy bandwidth (pinned host memory), by transfer size
  kernel   the per-read QC kernel from soa_pack.cpp on the GPU, over a real batch
           (soa_pack --dump). Decisions are checked against the CPU kernel's, read for read.
  bgzf     batched raw-Deflate decompression of BGZF blocks (nvCOMP "Deflate", RAW bitstream):
           the GPU equivalent of fastp's parallel BGZF reader
  gzip1    one ordinary single-member .fastq.gz (what sequencers produce) on the GPU: nvlzcat
           (nvCOMP >= 5.2 "lookahead" gzip, if on PATH) and nvCOMP's Python Gzip codec
  deflate  GPU compression of FASTQ text in fixed-size chunks (nvCOMP Deflate/GDeflate), ratio
           and throughput, i.e. what replacing fastp's libdeflate workers would give

Every section is optional and failures are recorded, not fatal, so one run gives whatever the
box supports. Needs: cupy (cupy-cuda12x), nvidia-nvcomp (pip), optionally nvlzcat.

Usage: gpu_bench.py --soa prefix [--bgzf file.bgzf.fastq.gz] [--gz file.fastq.gz]
                    [--plain file.fastq] [--json out.json] [--max-gb 4]
"""
import json, os, shutil, subprocess, sys, time
import numpy as np

try:
    import cupy as cp
except ImportError:
    sys.exit('needs cupy (pip install cupy-cuda12x)')


def opt(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


res = {'device': cp.cuda.runtime.getDeviceProperties(0)['name'].decode()}
MAX = int(float(opt('--max-gb', 4)) * 1e9)


def free_gpu():
    """Release cached device memory so the next section (or an nvlzcat subprocess) can use it."""
    import gc
    gc.collect()
    cp.get_default_memory_pool().free_all_blocks()
    cp.get_default_pinned_memory_pool().free_all_blocks()


def nbytes(x):
    """Size of an nvCOMP/CuPy device array without copying it to the host."""
    return int(cp.asarray(x).nbytes)


def timed(fn, reps=5):
    """Median seconds of fn() over reps, synchronised with CUDA events."""
    ts = []
    for _ in range(reps):
        s, e = cp.cuda.Event(), cp.cuda.Event()
        s.record(); fn(); e.record(); e.synchronize()
        ts.append(cp.cuda.get_elapsed_time(s, e) / 1e3)
    return sorted(ts)[len(ts) // 2]


# ---------------- pcie
pcie = {}
for mb in (16, 256, 1024):
    n = mb << 20
    h = cp.cuda.alloc_pinned_memory(n)
    hv = np.frombuffer(h, dtype=np.uint8, count=n)
    d = cp.empty(n, dtype=cp.uint8)
    h2d = timed(lambda: d.set(hv))
    d2h = timed(lambda: d.get(out=hv))
    pcie[f'{mb}MB'] = {'h2d_GBps': round(n / h2d / 1e9, 2), 'd2h_GBps': round(n / d2h / 1e9, 2)}
    del d
res['pcie'] = pcie
print('pcie', pcie, file=sys.stderr)

# ---------------- kernel
KERNEL = r'''
extern "C" __global__ void qc(const unsigned char* seq, const unsigned char* qual, const unsigned short* lens,
                              int n, int L, unsigned short* end_out, unsigned char* pass_out,
                              unsigned long long* qsum, unsigned long long* base) {
    extern __shared__ unsigned int sh[];           // qsum[L], base[4L] per block
    unsigned int* sq = sh; unsigned int* sb = sh + L;
    for (int i = threadIdx.x; i < 5 * L; i += blockDim.x) sh[i] = 0;
    __syncthreads();
    const char AD[13] = {'A','G','A','T','C','G','G','A','A','G','A','G','C'};
    for (int r = blockIdx.x * blockDim.x + threadIdx.x; r < n; r += gridDim.x * blockDim.x) {
        const unsigned char* s = seq + (size_t)r * L; const unsigned char* q = qual + (size_t)r * L;
        int len = lens[r], nN = 0, low = 0;
        for (int i = 0; i < len; i++) {
            nN += s[i] == 'N'; low += q[i] < 48;
            atomicAdd(&sq[i], (unsigned int)(q[i] - 33));
            atomicAdd(&sb[i * 4 + ((s[i] >> 1) & 3)], 1u);
        }
        int end = len, g = 0, mism = 0;
        for (int i = len - 1; i >= 0; i--) {
            if (s[i] == 'G') g++;
            else if (++mism > 1 + g / 8) break;
            else g++;
        }
        if (g >= 10) end = len - g;
        for (int p = 0; p + 4 <= end; p++) {
            int cmp = end - p < 13 ? end - p : 13, allowed = cmp / 8, mm = 0, k = 0;
            for (; k < cmp; k++) if (s[p + k] != AD[k] && ++mm > allowed) break;
            if (k == cmp) { end = p; break; }
        }
        end_out[r] = (unsigned short)end;
        pass_out[r] = (nN <= 5) && (low * 100 <= 40 * len) && (end >= 15);
    }
    __syncthreads();
    for (int i = threadIdx.x; i < L; i += blockDim.x) if (sq[i]) atomicAdd(&qsum[i], (unsigned long long)sq[i]);
    for (int i = threadIdx.x; i < 4 * L; i += blockDim.x) if (sb[i]) atomicAdd(&base[i], (unsigned long long)sb[i]);
}
'''
soa = opt('--soa')
if soa and os.path.exists(soa + '.soa'):
    raw = open(soa + '.soa', 'rb').read()
    n = int(np.frombuffer(raw, np.uint64, 1, 0)[0]); L = int(np.frombuffer(raw, np.uint32, 1, 8)[0])
    o = 12
    lens = np.frombuffer(raw, np.uint16, n, o); o += 2 * n
    seq = np.frombuffer(raw, np.uint8, n * L, o); o += n * L
    qual = np.frombuffer(raw, np.uint8, n * L, o)
    dec = np.frombuffer(open(soa + '.dec', 'rb').read(), dtype=np.dtype([('end', '<u2'), ('pass', 'u1'), ('pad', 'u1')]))
    k = cp.RawKernel(KERNEL, 'qc')
    dseq, dqual, dlens = cp.asarray(seq), cp.asarray(qual), cp.asarray(lens)
    dend, dpass = cp.empty(n, cp.uint16), cp.empty(n, cp.uint8)
    qsum, base = cp.zeros(L, cp.uint64), cp.zeros(4 * L, cp.uint64)
    sm = cp.cuda.runtime.getDeviceProperties(0)['multiProcessorCount']
    best = None
    for threads in (128, 256):
        for blocks_per_sm in (4, 8, 16):
            grid = sm * blocks_per_sm
            run = lambda: k((grid,), (threads,), (dseq, dqual, dlens, np.int32(n), np.int32(L), dend, dpass, qsum, base),
                            shared_mem=5 * L * 4)
            t = timed(run)
            if best is None or t < best[0]:
                best = (t, threads, grid)
    t, threads, grid = best
    qsum[:] = 0; base[:] = 0
    k((grid,), (threads,), (dseq, dqual, dlens, np.int32(n), np.int32(L), dend, dpass, qsum, base), shared_mem=5 * L * 4)
    cp.cuda.Device().synchronize()
    ends, passes = dend.get(), dpass.get()
    mismatch = int(np.sum((ends != dec['end']) | (passes != dec['pass'])))
    q = qual.reshape(n, L); ok = q > 0
    qsum_expect = int((q[ok].astype(np.int64) - 33).sum())
    h2d_bytes = seq.nbytes + qual.nbytes + lens.nbytes
    res['kernel'] = {
        'reads': n, 'L': L, 'threads': threads, 'grid': grid,
        'kernel_s': t, 'kernel_ns_per_read': t * 1e9 / n,
        'h2d_bytes_per_read': h2d_bytes / n, 'd2h_bytes_per_read': 3,
        'h2d_ns_per_read_at_measured_bw': h2d_bytes / n / (pcie['256MB']['h2d_GBps']),
        'decision_mismatches_vs_cpu': mismatch,
        'qsum_matches_cpu': int(qsum.get().sum()) == qsum_expect,
    }
    print('kernel', res['kernel'], file=sys.stderr)
    del dseq, dqual, dlens, dend, dpass, qsum, base
    free_gpu()

# ---------------- nvCOMP
try:
    from nvidia import nvcomp
    res['nvcomp_version'] = getattr(nvcomp, '__version__', '?')
except ImportError as e:
    nvcomp = None
    res['nvcomp_error'] = str(e)


def bgzf_blocks(path, limit):
    """Raw deflate payloads and uncompressed sizes of a BGZF file's blocks, up to `limit` bytes."""
    data = open(path, 'rb').read(limit)
    out, sizes, pos = [], [], 0
    while pos + 18 <= len(data):
        bsize = int.from_bytes(data[pos + 16:pos + 18], 'little') + 1
        if pos + bsize > len(data):
            break
        isize = int.from_bytes(data[pos + bsize - 4:pos + bsize], 'little')
        if isize:
            out.append(np.frombuffer(data, np.uint8, bsize - 26, pos + 18))
            sizes.append(isize)
        pos += bsize
    return out, sizes, pos


if nvcomp and opt('--bgzf'):
    try:
        chunks, sizes, comp_bytes = bgzf_blocks(opt('--bgzf'), MAX)
        codec = nvcomp.Codec(algorithm='Deflate', bitstream_kind=nvcomp.BitstreamKind.RAW)
        dchunks = [nvcomp.as_array(c).cuda() for c in chunks]
        cfg = codec.decompression_config(dchunks) if hasattr(codec, 'decompression_config') else None
        dec_fn = (lambda: codec.decode(dchunks, decompression_config=cfg)) if cfg is not None else (lambda: codec.decode(dchunks))
        out = dec_fn()
        got = sum(nbytes(x) for x in out)
        t = timed(dec_fn, reps=3)
        res['bgzf'] = {'blocks': len(chunks), 'compressed_bytes': comp_bytes, 'uncompressed_bytes': sum(sizes),
                       'size_ok': got == sum(sizes), 'decode_s': t, 'GBps_uncompressed': sum(sizes) / t / 1e9,
                       'note': 'device-resident input; add PCIe for compressed bytes'}
    except Exception as e:  # record, keep going
        res['bgzf'] = {'error': repr(e)}
    print('bgzf', res['bgzf'], file=sys.stderr)
    dchunks = out = None
    free_gpu()

if opt('--gz'):
    gz = opt('--gz'); g1 = {}
    usize = None
    if opt('--plain') and os.path.exists(opt('--plain')):
        usize = os.path.getsize(opt('--plain'))
    free_gpu()
    if shutil.which('nvlzcat'):
        # decompression is nvlzcat's default mode (-c would compress)
        runs = []
        for _ in range(3):
            s = time.time()
            p = subprocess.run(f'nvlzcat -f {gz} | wc -c', shell=True, capture_output=True, text=True)
            runs.append(time.time() - s)
        w = sorted(runs)[1]
        n = int(p.stdout.strip() or 0)
        g1['nvlzcat'] = {'wall_s': w, 'uncompressed_bytes': n, 'GBps_uncompressed': n / w / 1e9 if n else None,
                         'stderr': p.stderr[-300:], 'note': 'end to end from page cache: file read, PCIe, inflate, stdout'}
        if usize is not None and n != usize:
            g1['nvlzcat']['size_mismatch_vs_plain'] = usize
    else:
        g1['nvlzcat'] = 'not on PATH (nvCOMP >= 5.2 tarball ships it)'
    if nvcomp and opt('--plain'):
        # The Python API exposes no choice of gzip decompression algorithm (the LOOKAHEAD one is
        # in the C API and nvlzcat). Its default decodes a single-member stream as one chunk,
        # which on a whole multi-GB file ran for >15 min, so measure it on a 100 MB member.
        try:
            import gzip as _gz
            sample = np.fromfile(opt('--plain'), np.uint8, count=100_000_000).tobytes()
            member = np.frombuffer(_gz.compress(sample, compresslevel=4), np.uint8)
            codec = nvcomp.Codec(algorithm='Gzip', bitstream_kind=nvcomp.BitstreamKind.RAW)
            arr = nvcomp.as_array(member).cuda()
            out = codec.decode(arr)
            n = nbytes(out)
            t = timed(lambda: codec.decode(arr), reps=3)
            g1['python_gzip_codec_100MB_member'] = {
                'uncompressed_bytes': n, 'size_ok': n == len(sample), 'decode_s': t, 'GBps_uncompressed': n / t / 1e9,
                'note': 'default (non-lookahead) single-member decode, device-resident'}
        except Exception as e:
            g1['python_gzip_codec_100MB_member'] = {'error': repr(e)}
    arr = out = None
    free_gpu()
    res['gzip1'] = g1
    print('gzip1', g1, file=sys.stderr)

if nvcomp and opt('--plain'):
    data = np.fromfile(opt('--plain'), np.uint8, count=min(MAX // 4, os.path.getsize(opt('--plain'))))
    darr = nvcomp.as_array(data).cuda()
    comp = {}
    for alg in ('Deflate', 'GDeflate'):
        for chunk in (65536, 1 << 20):
          for atype in (1, 2, 4):
            try:
                # RAW chunks, like BGZF blocks without the 18/8-byte gzip framing
                codec = nvcomp.Codec(algorithm=alg, uncomp_chunk_size=chunk, algorithm_type=atype,
                                     bitstream_kind=nvcomp.BitstreamKind.RAW)
                enc = codec.encode(darr)
                t = timed(lambda: codec.encode(darr), reps=3)
                csize = nbytes(enc)
                comp[f'{alg}/{chunk}/t{atype}'] = {'in_bytes': int(data.size), 'out_bytes': csize,
                                                   'ratio': data.size / csize, 'encode_s': t, 'GBps_in': data.size / t / 1e9,
                                                   'note': 'device-resident; add PCIe for in/out bytes'}
            except Exception as e:
                comp[f'{alg}/{chunk}/t{atype}'] = {'error': repr(e)}
            enc = None
            free_gpu()
    darr = None
    free_gpu()
    if shutil.which('nvlzcat'):
        # streaming GPU gzip compression (nvCOMP >= 5.3), standard .gz output, levels 0 (fast) .. 5
        for a in (0, 1, 3):
            s = time.time()
            p = subprocess.run(f'nvlzcat -c -a {a} -f {opt("--plain")} | wc -c', shell=True, capture_output=True, text=True)
            w = time.time() - s
            outb = int(p.stdout.strip() or 0)
            insz = os.path.getsize(opt('--plain'))
            comp[f'nvlzcat-gzip/a{a}'] = {'in_bytes': insz, 'out_bytes': outb, 'ratio': insz / outb if outb else None,
                                          'wall_s': w, 'GBps_in': insz / w / 1e9, 'stderr': p.stderr[-300:],
                                          'note': 'end to end, whole file'}
    res['deflate'] = comp
    print('deflate', comp, file=sys.stderr)

js = json.dumps(res, indent=1, default=float)
print(js)
if opt('--json'):
    open(opt('--json'), 'w').write(js)
