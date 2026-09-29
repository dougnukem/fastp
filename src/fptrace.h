#ifndef FASTP_TRACE_H
#define FASTP_TRACE_H

// Thread naming (always on) and opt-in per-pack tracing (`make TRACE=1`).
//
// Thread names (fp-read-L, fp-work-3, fp-bgzf, fp-write, ...) show up in top -H, pidstat -t,
// perf and gdb, so CPU can be attributed to a pipeline stage without a trace build.
//
// With -DFASTP_TRACE, each thread records timed spans into its own buffer (no locks on the
// hot path; one steady_clock read at each end of a span). At exit the buffers are written as
// TSV to $FASTP_TRACE_FILE (default fastp.trace.tsv):
//     thread  kind  t0_ns  t1_ns  a  b
// where a/b are per-kind counts (reads, bytes in/out). Spans on one thread can nest (e.g.
// compress inside process); benchmark/scripts/trace_analyze.py computes exclusive time.
// Without FASTP_TRACE every macro compiles to nothing.

#include <cstdint>

#if defined(__linux__)
#include <pthread.h>
#elif defined(__APPLE__)
#include <pthread.h>
#endif

#ifdef FASTP_TRACE
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <string>
#include <vector>
#endif

namespace fptrace {

enum Kind : uint8_t {
    READ_PACK,      // reader: from the first read of a pack until it is handed to a worker (a=reads)
    DECOMPRESS,     // reader: inflate of ordinary gzip into the parse buffer (a=bytes out)
    BGZF_FETCH,     // reader: waiting for/copying blocks from the BGZF pool (a=bytes out)
    READER_WAIT,    // reader: backpressure sleep (workers or writers behind)
    PROCESS,        // worker: one pack (or pair of packs) trimmed/filtered/stats/serialised (a=reads)
    WORKER_WAIT,    // worker: nothing to consume
    COMPRESS,       // worker (pwrite mode) or writer: libdeflate gzip (a=bytes in, b=bytes out)
    OFFSET_WAIT,    // worker (pwrite mode): waiting for the previous pack's output offset
    WRITE,          // pwrite / fwrite of output bytes (a=bytes)
    BGZF_BLOCK,     // BGZF pool thread: one 64KB block inflated (a=bytes out)
    KIND_COUNT
};

static const char* const KIND_NAMES[KIND_COUNT] = {
    "read_pack", "decompress", "bgzf_fetch", "reader_wait", "process", "worker_wait",
    "compress", "offset_wait", "write", "bgzf_block"};

#ifdef FASTP_TRACE

struct Event { uint64_t t0, t1, a, b; uint8_t kind; };
struct Buffer { std::string name; std::vector<Event> events; };

inline uint64_t now() {
    static const auto start = std::chrono::steady_clock::now();
    return (uint64_t)std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now() - start).count();
}

inline void dump();

struct Registry {
    std::mutex mtx;
    std::vector<Buffer*> buffers;
    static Registry& get() {
        static Registry* r = [] { now(); std::atexit(dump); return new Registry(); }();
        return *r;
    }
};

// Buffers outlive their threads (owned by the registry) so they can be written at exit.
inline Buffer* local() {
    thread_local Buffer* b = nullptr;
    if (!b) {
        b = new Buffer();
        b->name = "fastp";
        b->events.reserve(1 << 14);
        Registry& r = Registry::get();
        std::lock_guard<std::mutex> lk(r.mtx);
        r.buffers.push_back(b);
    }
    return b;
}

inline void dump() {
    Registry& r = Registry::get();
    const char* path = std::getenv("FASTP_TRACE_FILE");
    FILE* f = std::fopen(path ? path : "fastp.trace.tsv", "w");
    if (!f) return;
    std::fprintf(f, "thread\tkind\tt0_ns\tt1_ns\ta\tb\n");
    std::lock_guard<std::mutex> lk(r.mtx);
    for (size_t i = 0; i < r.buffers.size(); i++) {
        Buffer* b = r.buffers[i];
        // make names unique per thread instance: fp-work-3 stays, repeated names get #i
        std::string name = b->name + "#" + std::to_string(i);
        for (const Event& e : b->events)
            std::fprintf(f, "%s\t%s\t%llu\t%llu\t%llu\t%llu\n", name.c_str(), KIND_NAMES[e.kind],
                         (unsigned long long)e.t0, (unsigned long long)e.t1,
                         (unsigned long long)e.a, (unsigned long long)e.b);
    }
    std::fclose(f);
}

// For spans that cross loop iterations: t0 = fptrace::now(); ... fptrace::record(KIND, t0, n);
inline void record(Kind k, uint64_t t0, uint64_t a = 0, uint64_t b = 0) {
    local()->events.push_back(Event{t0, now(), a, b, (uint8_t)k});
}

struct Span {
    Kind kind; uint64_t t0; uint64_t a = 0, b = 0;
    explicit Span(Kind k) : kind(k), t0(now()) {}
    ~Span() { local()->events.push_back(Event{t0, now(), a, b, (uint8_t)kind}); }
    Span(const Span&) = delete;
    Span& operator=(const Span&) = delete;
};

#else

inline uint64_t now() { return 0; }
inline void record(Kind, uint64_t, uint64_t = 0, uint64_t = 0) {}

struct Span {
    uint64_t a = 0, b = 0;
    explicit Span(Kind) {}
};

#endif

// Names the calling thread (≤15 chars on Linux) for tools, and for the trace.
inline void setThreadName(const char* name) {
#if defined(__linux__)
    pthread_setname_np(pthread_self(), name);
#elif defined(__APPLE__)
    pthread_setname_np(name);
#endif
#ifdef FASTP_TRACE
    local()->name = name;
#endif
}

} // namespace fptrace

#define FPTRACE_CAT2(a, b) a##b
#define FPTRACE_CAT(a, b) FPTRACE_CAT2(a, b)
// Times the rest of the enclosing scope as `kind`.
#define FPTRACE_SPAN(kind) fptrace::Span FPTRACE_CAT(fptrace_span_, __LINE__)(fptrace::kind)
// Same, with a handle to set the span's a/b counters: FPTRACE_NAMED(s, COMPRESS); s.a = n;
#define FPTRACE_NAMED(var, kind) fptrace::Span var(fptrace::kind)

#endif
