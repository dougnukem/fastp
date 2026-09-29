// Measures the CPU cost of the data transformations a GPU (or other batch accelerator) path
// would add to fastp, on real reads, per read:
//
//   index    find record boundaries in FASTQ text (what any parser must do first)
//   pack     gather reads into a fixed-stride structure-of-arrays batch: seq[N][L], qual[N][L],
//            len[N]. This is the layout a GPU kernel wants and what is copied host -> device.
//   pack2    same, but sequence 2-bit encoded (4 bases/byte) plus an N mask; quality kept 8-bit
//   kernel   a representative per-read QC kernel on the SoA batch (see below): the same work the
//            GPU benchmark (gpu_bench.py) runs, so the two can be compared read for read
//   emit     serialise the kept reads back to FASTQ text using the kernel's trim decisions
//            (only decisions come back from a device, the text is rebuilt on the host)
//
// The kernel is an analogue of fastp's default per-read work, not a port: N count and
// low-quality fraction filters, polyG tail trim, adapter search with mismatches (fastp's
// trimBySequence style), per-position quality sums and base counts. fastp's own per-read cost
// comes from the trace build (trace_analyze.py, process_ns_per_read); the ratio between this
// kernel on CPU and on GPU is what the cost model applies to it.
//
// Build: g++ -O3 -march=native -std=c++17 -o soa_pack soa_pack.cpp
// Usage: soa_pack <reads.fastq> [batch_reads=1048576] [--dump prefix]
//   --dump writes the first batch as prefix.soa (binary, see write_dump) and the CPU kernel's
//   decisions as prefix.dec, so gpu_bench.py can check the GPU kernel gives identical results.
// Prints one JSON object with ns/read per phase, bytes per read per layout, and totals.
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

using clk = std::chrono::steady_clock;
static double secs(clk::time_point a, clk::time_point b) { return std::chrono::duration<double>(b - a).count(); }

struct Rec { uint64_t name, seq, qual; uint32_t nameLen, len; };

// Kernel parameters (fastp defaults where one exists)
static const int QUAL_OK = 15 + 33;        // --qualified_quality_phred 15
static const int UNQUAL_PCT = 40;          // --unqualified_percent_limit 40
static const int N_LIMIT = 5;              // --n_base_limit 5
static const int MIN_LEN = 15;             // --length_required 15
static const char ADAPTER[] = "AGATCGGAAGAGC";  // TruSeq prefix
static const int ADAPTER_LEN = 13;
static const int POLYG_MIN = 10;

struct Decision { uint16_t end; uint8_t pass; uint8_t pad; };

// One read. Mirrors kernel_qc in gpu_bench.py exactly; keep the two in step.
static inline Decision qc(const uint8_t* s, const uint8_t* q, int len, uint64_t* qsum, uint32_t* base) {
    int nN = 0, low = 0;
    for (int i = 0; i < len; i++) {
        nN += s[i] == 'N';
        low += q[i] < QUAL_OK;
        qsum[i] += q[i] - 33;
        base[i * 4 + ((s[i] >> 1) & 3)]++;  // A=0 C=1 T=2 G=3 (N folds into G's slot, as a cheap hash)
    }
    int end = len;
    // polyG tail
    int g = 0, mism = 0;
    for (int i = len - 1; i >= 0; i--) {
        if (s[i] == 'G') g++;
        else if (++mism > 1 + g / 8) break;
        else g++;
    }
    if (g >= POLYG_MIN) end = len - g;
    // adapter: first position where the adapter (or its prefix running off the end) matches
    // with at most 1 mismatch per 8 compared bases
    for (int p = 0; p + 4 <= end; p++) {
        int cmp = end - p < ADAPTER_LEN ? end - p : ADAPTER_LEN;
        int allowed = cmp / 8, mm = 0;
        int k = 0;
        for (; k < cmp; k++) {
            if (s[p + k] != (uint8_t)ADAPTER[k] && ++mm > allowed) break;
        }
        if (k == cmp) { end = p; break; }
    }
    Decision d;
    d.end = (uint16_t)end;
    d.pass = (nN <= N_LIMIT) && (low * 100 <= UNQUAL_PCT * len) && (end >= MIN_LEN);
    d.pad = 0;
    return d;
}

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "usage: soa_pack <reads.fastq> [batch_reads] [--dump prefix]\n"); return 1; }
    size_t batch = argc > 2 && argv[2][0] != '-' ? strtoull(argv[2], 0, 10) : (1u << 20);
    const char* dump = nullptr;
    for (int i = 1; i < argc - 1; i++) if (!strcmp(argv[i], "--dump")) dump = argv[i + 1];

    FILE* f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 1; }
    fseek(f, 0, SEEK_END); size_t fsz = ftell(f); fseek(f, 0, SEEK_SET);
    std::vector<char> buf(fsz + 1);
    if (fread(buf.data(), 1, fsz, f) != fsz) { perror("read"); return 1; }
    fclose(f);
    const char* b = buf.data();

    double tIndex = 0, tPack = 0, tPack2 = 0, tKernel = 0, tEmit = 0;
    uint64_t reads = 0, kept = 0, emitted = 0, maxLen = 0, bases = 0;
    std::vector<Rec> recs; recs.reserve(batch);
    std::vector<uint8_t> seq, qual, seq2, nmask; std::vector<uint16_t> lens;
    std::vector<Decision> dec;
    std::vector<uint64_t> qsum(1024); std::vector<uint32_t> base(4096);
    std::string out; out.reserve(batch * 400);
    bool dumped = false;

    size_t pos = 0;
    while (pos < fsz) {
        // ---- index: 4 lines per record
        auto t0 = clk::now();
        recs.clear();
        uint32_t L = 0;
        while (pos < fsz && recs.size() < batch) {
            Rec r;
            const char* e;
            r.name = pos; e = (const char*)memchr(b + pos, '\n', fsz - pos); if (!e) break;
            r.nameLen = (uint32_t)(e - (b + pos)); pos = e - b + 1;
            r.seq = pos; e = (const char*)memchr(b + pos, '\n', fsz - pos); if (!e) break;
            r.len = (uint32_t)(e - (b + pos)); pos = e - b + 1;
            e = (const char*)memchr(b + pos, '\n', fsz - pos); if (!e) break; pos = e - b + 1;
            r.qual = pos; e = (const char*)memchr(b + pos, '\n', fsz - pos);
            size_t qualLen = (e ? (size_t)(e - b) : fsz) - r.qual;
            pos = e ? (size_t)(e - b + 1) : fsz;
            if (qualLen != r.len) { fprintf(stderr, "skipping malformed record at byte %llu\n", (unsigned long long)r.name); continue; }
            if (r.len > L) L = r.len;
            recs.push_back(r);
        }
        size_t n = recs.size();
        if (!n) break;
        auto t1 = clk::now();

        // ---- pack: fixed-stride SoA, zero padded
        seq.assign(n * L, 0); qual.assign(n * L, 0); lens.resize(n);
        for (size_t i = 0; i < n; i++) {
            memcpy(&seq[i * L], b + recs[i].seq, recs[i].len);
            memcpy(&qual[i * L], b + recs[i].qual, recs[i].len);
            lens[i] = (uint16_t)recs[i].len;
        }
        auto t2 = clk::now();

        // ---- pack2: 2-bit sequence + N mask (bit per base), qual unchanged
        size_t L4 = (L + 3) / 4, L8 = (L + 7) / 8;
        seq2.assign(n * L4, 0); nmask.assign(n * L8, 0);
        for (size_t i = 0; i < n; i++) {
            const uint8_t* s = (const uint8_t*)b + recs[i].seq;
            uint8_t* o = &seq2[i * L4]; uint8_t* m = &nmask[i * L8];
            for (uint32_t j = 0; j < recs[i].len; j++) {
                o[j >> 2] |= ((s[j] >> 1) & 3) << ((j & 3) * 2);
                if (s[j] == 'N') m[j >> 3] |= 1 << (j & 7);
            }
        }
        auto t3 = clk::now();

        // ---- kernel on the SoA batch
        if (L > qsum.size()) { qsum.resize(L); base.resize(L * 4); }
        dec.resize(n);
        for (size_t i = 0; i < n; i++) dec[i] = qc(&seq[i * L], &qual[i * L], lens[i], qsum.data(), base.data());
        auto t4 = clk::now();

        // ---- emit kept reads as FASTQ text using the decisions
        out.clear();
        for (size_t i = 0; i < n; i++) {
            if (!dec[i].pass) continue;
            const Rec& r = recs[i];
            out.append(b + r.name, r.nameLen); out.push_back('\n');
            out.append(b + r.seq, dec[i].end); out.append("\n+\n", 3);
            out.append(b + r.qual, dec[i].end); out.push_back('\n');
            kept++;
        }
        emitted += out.size();
        auto t5 = clk::now();

        if (dump && !dumped) {
            // prefix.soa: uint64 n, uint32 L, uint16 len[n], uint8 seq[n*L], uint8 qual[n*L]
            std::string p = std::string(dump) + ".soa";
            FILE* d = fopen(p.c_str(), "wb");
            uint64_t nn = n; fwrite(&nn, 8, 1, d); fwrite(&L, 4, 1, d);
            fwrite(lens.data(), 2, n, d); fwrite(seq.data(), 1, n * L, d); fwrite(qual.data(), 1, n * L, d);
            fclose(d);
            p = std::string(dump) + ".dec";  // Decision[n]
            d = fopen(p.c_str(), "wb"); fwrite(dec.data(), sizeof(Decision), n, d); fclose(d);
            dumped = true;
        }

        tIndex += secs(t0, t1); tPack += secs(t1, t2); tPack2 += secs(t2, t3);
        tKernel += secs(t3, t4); tEmit += secs(t4, t5);
        reads += n; if (L > maxLen) maxLen = L;
        for (size_t i = 0; i < n; i++) bases += recs[i].len;
    }
    double ns = 1e9 / (double)reads;
    uint64_t chk = 0; for (auto v : qsum) chk += v;
    printf("{\"file_bytes\": %zu, \"reads\": %llu, \"bases\": %llu, \"max_len\": %llu, \"batch_reads\": %zu,\n",
           fsz, (unsigned long long)reads, (unsigned long long)bases, (unsigned long long)maxLen, batch);
    printf(" \"kept\": %llu, \"emitted_bytes\": %llu, \"qsum_check\": %llu,\n",
           (unsigned long long)kept, (unsigned long long)emitted, (unsigned long long)chk);
    printf(" \"ns_per_read\": {\"index\": %.1f, \"pack\": %.1f, \"pack2\": %.1f, \"kernel\": %.1f, \"emit\": %.1f},\n",
           tIndex * ns, tPack * ns, tPack2 * ns, tKernel * ns, tEmit * ns);
    double text = (double)fsz / reads, L = (double)maxLen;
    printf(" \"bytes_per_read\": {\"fastq_text\": %.1f, \"soa_fixed\": %.1f, \"soa_2bit\": %.1f, \"decisions\": %zu}}\n",
           text, 2 * L + 2, (L + 3) / 4 + (L + 7) / 8 + L + 2, sizeof(Decision));
    return 0;
}
