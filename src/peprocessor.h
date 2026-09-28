#ifndef PE_PROCESSOR_H
#define PE_PROCESSOR_H

#include <stdio.h>
#include <stdlib.h>
#include <string>
#include "read.h"
#include <cstdlib>
#include <condition_variable>
#include <mutex>
#include <thread>
#include "options.h"
#include "threadconfig.h"
#include "filter.h"
#include "umiprocessor.h"
#include "overlapanalysis.h"
#include "writerthread.h"
#include "duplicate.h"
#include "readpool.h"
#include "packring.h"


using namespace std;

typedef struct ReadPairRepository ReadPairRepository;

class PairEndProcessor{
public:
    PairEndProcessor(Options* opt);
    ~PairEndProcessor();
    bool process();

private:
    bool processPairEnd(ReadPack* leftPack, ReadPack* rightPack, ThreadConfig* config);
    void readerTask(bool isLeft);
    void interleavedReaderTask();
    void processorTask(ThreadConfig* config);
    void initConfig(ThreadConfig* config);
    void initOutput();
    void closeOutput();
    void statInsertSize(Read* r1, Read* r2, OverlapResult& ov, int frontTrimmed1 = 0, int frontTrimmed2 = 0);
    int getPeakInsertSize();
    void writerTask(WriterThread* config);
    void recycleToPool1(int tid, Read* r);
    void recycleToPool2(int tid, Read* r);

private:
    atomic_bool mLeftReaderFinished;
    atomic_bool mRightReaderFinished;
    alignas(128) atomic_int mFinishedThreads;
    Options* mOptions;
    Filter* mFilter;
    UmiProcessor* mUmiProcessor;
    atomic_long* mInsertSizeHist;
    WriterThread* mLeftWriter;
    WriterThread* mRightWriter;
    WriterThread* mUnpairedLeftWriter;
    WriterThread* mUnpairedRightWriter;
    WriterThread* mMergedWriter;
    WriterThread* mFailedWriter;
    WriterThread* mOverlappedWriter;
    Duplicate* mDuplicate;
    // Readers publish packs by sequence number; workers claim sequence numbers
    // (dynamically via mNextClaim, or statically t, t+W, ... when split output
    // needs a fixed pack-to-worker mapping) and take them from these rings.
    PackRing* mLeftRing;
    PackRing* mRightRing;
    alignas(128) std::atomic<size_t> mNextClaim;
    bool mStaticSchedule;
    size_t mLeftPackReadCounter;
    size_t mRightPackReadCounter;
    alignas(128) atomic_long mPackProcessedCounter;
    long mPackInMemLimit;
    int mPackSize;
    ReadPool* mLeftReadPool;
    ReadPool* mRightReadPool;
    atomic_bool shouldStopReading;
    std::mutex mBackpressureMtx;
    std::condition_variable mBackpressureCV;
};


#endif