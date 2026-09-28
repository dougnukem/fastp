#ifndef PACK_RING_H
#define PACK_RING_H

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include "read.h"

// Fixed-size ring of ReadPack slots indexed by pack sequence number, replacing
// per-worker push queues. One reader thread publishes pack `seq` into slot
// seq % size; whichever worker claimed `seq` takes it. Because workers pull by
// sequence number instead of readers pushing into a chosen worker's queue,
// there is no "last item in a queue isn't consumable until another arrives"
// invariant to satisfy (the root cause of #721), and a slow worker can't strand
// a pack that every later write is waiting on.
class PackRing {
public:
    explicit PackRing(size_t size) : mSize(size) { mSlots = new Slot[size]; }
    ~PackRing() { delete[] mSlots; }

    // Blocks until the slot's previous occupant (seq - size) has been taken.
    void publish(size_t seq, ReadPack* pack) {
        Slot& s = mSlots[seq % mSize];
        if (s.seq.load(std::memory_order_acquire) != SIZE_MAX) {
            std::unique_lock<std::mutex> lk(mMtx);
            mCV.wait(lk, [&] { return s.seq.load(std::memory_order_acquire) == SIZE_MAX; });
        }
        s.pack = pack;
        s.seq.store(seq, std::memory_order_release);
        mPublished.store(seq + 1, std::memory_order_release);
        notify();
    }

    // Called by the producer after its last publish().
    void finish() {
        mFinished.store(true, std::memory_order_release);
        notify();
    }

    // Returns pack `seq`, or NULL if the producer finished without publishing it.
    ReadPack* take(size_t seq) {
        Slot& s = mSlots[seq % mSize];
        if (!ready(s, seq)) {
            std::unique_lock<std::mutex> lk(mMtx);
            mCV.wait(lk, [&] { return ready(s, seq); });
        }
        if (s.seq.load(std::memory_order_acquire) != seq)
            return NULL;
        ReadPack* pack = s.pack;
        s.seq.store(SIZE_MAX, std::memory_order_release);
        notify();
        return pack;
    }

private:
    struct alignas(64) Slot {
        std::atomic<size_t> seq{SIZE_MAX};
        ReadPack* pack = NULL;
    };

    bool ready(Slot& s, size_t seq) {
        return s.seq.load(std::memory_order_acquire) == seq ||
               (mFinished.load(std::memory_order_acquire) &&
                mPublished.load(std::memory_order_acquire) <= seq);
    }

    // Lock before notifying so a waiter can't check its predicate, miss this
    // update, and then sleep through the notification.
    void notify() {
        { std::lock_guard<std::mutex> lk(mMtx); }
        mCV.notify_all();
    }

    Slot* mSlots;
    size_t mSize;
    std::atomic<size_t> mPublished{0};
    std::atomic<bool> mFinished{false};
    std::mutex mMtx;
    std::condition_variable mCV;
};

#endif
