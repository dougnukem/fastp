window.BENCHMARK_DATA = {
  "lastUpdate": 1790920036748,
  "repoUrl": "https://github.com/dougnukem/fastp",
  "entries": {
    "Benchmark": [
      {
        "commit": {
          "author": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "committer": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "distinct": true,
          "id": "1166af0f8c2844f407e5ef70c5a54884a7b26b0c",
          "message": "fix(ci): benchmark tracking on master, and alternate run order\n\n- github-action-benchmark runs git in the workspace root, so check the PR\n  out there (base goes to _base/) and keep results in $RUNNER_TEMP, out of\n  reach of its gh-pages switch.\n- Alternate base/head order each rep. With base always first, every PR\n  showed processing 1-4% slower than base, including ones that don't touch\n  that path.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
          "timestamp": "2026-09-28T16:14:05-05:00",
          "tree_id": "b29ae5c616884cf01fddebc3fbab4b77358fbe33",
          "url": "https://github.com/dougnukem/fastp/commit/1166af0f8c2844f407e5ef70c5a54884a7b26b0c"
        },
        "date": 1790630417160,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "synthetic_pe -w1 wall time",
            "value": 4.612,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 CPU (user+sys)",
            "value": 7.515,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 peak RSS",
            "value": 1238.449,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w1 adapter detection",
            "value": 0.938,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 processing",
            "value": 3.552,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 wall time",
            "value": 3.142,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 CPU (user+sys)",
            "value": 8.783,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 peak RSS",
            "value": 1232.457,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w4 adapter detection",
            "value": 0.936,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 processing",
            "value": 2.118,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 wall time",
            "value": 2.255,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 CPU (user+sys)",
            "value": 3.296,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 peak RSS",
            "value": 1198.875,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w1 adapter detection",
            "value": 0.568,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 processing",
            "value": 1.599,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 wall time",
            "value": 1.746,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 CPU (user+sys)",
            "value": 4.45,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 peak RSS",
            "value": 1194.32,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w4 adapter detection",
            "value": 0.572,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 processing",
            "value": 1.115,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 wall time",
            "value": 4.561,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 CPU (user+sys)",
            "value": 7.612,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 peak RSS",
            "value": 1227.113,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w1 adapter detection",
            "value": 0.719,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 processing",
            "value": 3.708,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 wall time",
            "value": 2.964,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 CPU (user+sys)",
            "value": 8.636,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 peak RSS",
            "value": 1217.828,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w4 adapter detection",
            "value": 0.725,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 processing",
            "value": 2.153,
            "unit": "s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "committer": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "distinct": true,
          "id": "13c83aca6a966db3c0b703d9dda19a6ad75d3fb1",
          "message": "Merge remote-tracking branch 'origin/benchmark/corpus-and-release-backfill' into fork-main",
          "timestamp": "2026-09-28T21:03:04-05:00",
          "tree_id": "22071ec133a6d1803bf8e70576761d8808feb45a",
          "url": "https://github.com/dougnukem/fastp/commit/13c83aca6a966db3c0b703d9dda19a6ad75d3fb1"
        },
        "date": 1790647571877,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "synthetic_pe -w1 wall time",
            "value": 3.548,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 CPU (user+sys)",
            "value": 5.261,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 peak RSS",
            "value": 1239.035,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w1 adapter detection",
            "value": 0.386,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 processing",
            "value": 3.085,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 wall time",
            "value": 1.986,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 CPU (user+sys)",
            "value": 6.157,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 peak RSS",
            "value": 1233.223,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w4 adapter detection",
            "value": 0.384,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 processing",
            "value": 1.537,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 wall time",
            "value": 1.657,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 CPU (user+sys)",
            "value": 2.317,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 peak RSS",
            "value": 1199.488,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w1 adapter detection",
            "value": 0.22,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 processing",
            "value": 1.385,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 wall time",
            "value": 1.016,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 CPU (user+sys)",
            "value": 2.913,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 peak RSS",
            "value": 1195.621,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w4 adapter detection",
            "value": 0.217,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 processing",
            "value": 0.758,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 wall time",
            "value": 3.47,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 CPU (user+sys)",
            "value": 5.196,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 peak RSS",
            "value": 1226.637,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w1 adapter detection",
            "value": 0.262,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 processing",
            "value": 3.115,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 wall time",
            "value": 1.835,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 CPU (user+sys)",
            "value": 5.979,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 peak RSS",
            "value": 1219.086,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w4 adapter detection",
            "value": 0.256,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 processing",
            "value": 1.52,
            "unit": "s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "committer": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "distinct": true,
          "id": "4206179fef4a2793ddeb38f5fbf70b6cf309fef0",
          "message": "feat(bench): project subset results to a full-size run and gate on that\n\nSubsets overstate changes to fixed-cost stages: pre-processing, adapter\ndetection (capped at 256K reads / 39.6M bases per mate) and the report cost\nthe same on a subset as on a full run. Each run is now also projected to a\nfull-size run (--project-reads, default 50M reads or pairs): fixed stages as\nmeasured plus processing scaled by read count. The report and the gate use\nprojected wall and CPU; measured subset numbers move to a collapsed section.\n\nChecked against 30 full-size public runs (6 datasets, 2 builds, -w 8/16/48):\nprojected wall within 8% of measured (median); base-vs-head deltas within\n3 percentage points, against 10 points for raw subset deltas.\n\nThe synthetic set grows to 300K pairs so detection reaches its cap, as it\ndoes on a full file.\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>",
          "timestamp": "2026-09-29T10:55:54-05:00",
          "tree_id": "4c85e09cf4a7e061bee8b43d388d17f921f648fe",
          "url": "https://github.com/dougnukem/fastp/commit/4206179fef4a2793ddeb38f5fbf70b6cf309fef0"
        },
        "date": 1790697651619,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "synthetic_pe -w1 projected wall",
            "value": 755.818,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 projected CPU",
            "value": 1176.898,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 peak RSS",
            "value": 1275.797,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w1 wall time",
            "value": 5.101,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 CPU (user+sys)",
            "value": 7.627,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 adapter detection",
            "value": 0.504,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w1 processing",
            "value": 4.531,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 projected wall",
            "value": 373.991,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 projected CPU",
            "value": 1409.925,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 peak RSS",
            "value": 1272.395,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w4 wall time",
            "value": 2.822,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 CPU (user+sys)",
            "value": 9.043,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 adapter detection",
            "value": 0.499,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 processing",
            "value": 2.241,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 projected wall",
            "value": 326.739,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 projected CPU",
            "value": 489.101,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 peak RSS",
            "value": 1235.875,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w1 wall time",
            "value": 2.286,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 CPU (user+sys)",
            "value": 3.26,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 adapter detection",
            "value": 0.288,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w1 processing",
            "value": 1.958,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 projected wall",
            "value": 180.242,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 projected CPU",
            "value": 651.951,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 peak RSS",
            "value": 1233.266,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w4 wall time",
            "value": 1.415,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 CPU (user+sys)",
            "value": 4.236,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 adapter detection",
            "value": 0.284,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 processing",
            "value": 1.079,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 projected wall",
            "value": 308.453,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 projected CPU",
            "value": 486.442,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 peak RSS",
            "value": 1226.969,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w1 wall time",
            "value": 3.433,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 CPU (user+sys)",
            "value": 5.213,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 adapter detection",
            "value": 0.26,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w1 processing",
            "value": 3.081,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 projected wall",
            "value": 155.131,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 projected CPU",
            "value": 566.399,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 peak RSS",
            "value": 1219.621,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w4 wall time",
            "value": 1.863,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 CPU (user+sys)",
            "value": 5.976,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 adapter detection",
            "value": 0.255,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 processing",
            "value": 1.548,
            "unit": "s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "committer": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "distinct": true,
          "id": "1dacad6a5a087f89218de407b05525d2bec2348e",
          "message": "feat(bench): fit a line through two subset sizes; gate on CPU per pair\n\nProjecting one subset run needed stage timestamps and still overpredicted\nsome datasets. Each build is now run on the first 0.3M and 1.2M pairs of the\nsame input (--reads_to_process, no recompression; both above the 256K-read\ndetection cap), and a line through the two points gives a fixed cost\n(intercept) and a cost per pair (slope). Projected wall, CPU per pair and\npeak RSS are gated; the fixed cost and the measured subset numbers are shown\nin collapsed sections.\n\nOn 3 complete public runs at 4 and 16 cores, a line through two subset sizes\npredicted full-run CPU within 1-2% and wall within 2-4% (median error),\nagainst 3% and 11% for scaling a single subset.\n\n- Only -w 4 is run: CPU per pair doesn't depend on the thread count, and\n  -w 1 was the slowest cell.\n- gen_reads.py draws qualities from a pool built once instead of 150\n  Gaussians per read: 4x faster, so a 1.2M-pair file takes about 2 minutes.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>",
          "timestamp": "2026-10-02T00:00:51-05:00",
          "tree_id": "4171785172349d36eff017bb35bb9afbe10a93c8",
          "url": "https://github.com/dougnukem/fastp/commit/1dacad6a5a087f89218de407b05525d2bec2348e"
        },
        "date": 1790917691018,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "synthetic_pe -w4 projected wall",
            "value": 498.023,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 CPU per pair (read for SE)",
            "value": 38.654,
            "unit": "µs"
          },
          {
            "name": "synthetic_pe -w4 peak RSS",
            "value": 1286.016,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w4 fixed cost (wall)",
            "value": 1.01,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 projected CPU",
            "value": 1933.733,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 wall time",
            "value": 12.938,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 CPU (user+sys)",
            "value": 47.435,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 adapter detection",
            "value": 0.803,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 processing",
            "value": 12.007,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 projected wall",
            "value": 243.99,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 CPU per pair (read for SE)",
            "value": 18.841,
            "unit": "µs"
          },
          {
            "name": "synthetic_se -w4 peak RSS",
            "value": 1240.227,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w4 fixed cost (wall)",
            "value": 0.641,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 projected CPU",
            "value": 942.681,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 wall time",
            "value": 6.478,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 CPU (user+sys)",
            "value": 23.229,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 adapter detection",
            "value": 0.449,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 processing",
            "value": 5.956,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 projected wall",
            "value": 202.492,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 CPU per pair (read for SE)",
            "value": 15.651,
            "unit": "µs"
          },
          {
            "name": "atac_hiseq_pe -w4 peak RSS",
            "value": 1218.914,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w4 fixed cost (wall)",
            "value": 0.625,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 projected CPU",
            "value": 783.192,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 wall time",
            "value": 5.474,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 CPU (user+sys)",
            "value": 19.431,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 adapter detection",
            "value": 0.438,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 processing",
            "value": 4.95,
            "unit": "s"
          }
        ]
      },
      {
        "commit": {
          "author": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "committer": {
            "email": "noreply@anthropic.com",
            "name": "Claude",
            "username": "claude"
          },
          "distinct": true,
          "id": "6624a53143aafee095d576627f57e4e323bf09a4",
          "message": "fix(bench): survive an unavailable input; restart on 416; cache only complete sets\n\nThe ENA stream for the public input can be left half-populated when two jobs\nstart pulling the same file at once: the first connection returns a few KB and\nevery ranged request then gets 416 Range Not Satisfiable. A PR's CI shouldn't\nfail on that.\n\n- On 416, restart the download from byte 0 instead of retrying the same offset.\n- If an input still can't be fetched, skip that dataset with a warning, say so\n  in the report, and run the rest.\n- Cache the datasets only when the set is complete (separate restore and save\n  steps), so a skipped input is retried on the next run.\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>",
          "timestamp": "2026-10-02T00:39:21-05:00",
          "tree_id": "1a5efb150c0d61092be7160bf19fb514c3d795bf",
          "url": "https://github.com/dougnukem/fastp/commit/6624a53143aafee095d576627f57e4e323bf09a4"
        },
        "date": 1790920036039,
        "tool": "customSmallerIsBetter",
        "benches": [
          {
            "name": "synthetic_pe -w4 projected wall",
            "value": 494.187,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 CPU per pair (read for SE)",
            "value": 38.646,
            "unit": "µs"
          },
          {
            "name": "synthetic_pe -w4 peak RSS",
            "value": 1286.227,
            "unit": "MB"
          },
          {
            "name": "synthetic_pe -w4 fixed cost (wall)",
            "value": 1.034,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 projected CPU",
            "value": 1933.331,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 wall time",
            "value": 12.87,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 CPU (user+sys)",
            "value": 47.386,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 adapter detection",
            "value": 0.802,
            "unit": "s"
          },
          {
            "name": "synthetic_pe -w4 processing",
            "value": 11.941,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 projected wall",
            "value": 243.826,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 CPU per pair (read for SE)",
            "value": 18.793,
            "unit": "µs"
          },
          {
            "name": "synthetic_se -w4 peak RSS",
            "value": 1240.227,
            "unit": "MB"
          },
          {
            "name": "synthetic_se -w4 fixed cost (wall)",
            "value": 0.636,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 projected CPU",
            "value": 940.264,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 wall time",
            "value": 6.473,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 CPU (user+sys)",
            "value": 23.168,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 adapter detection",
            "value": 0.449,
            "unit": "s"
          },
          {
            "name": "synthetic_se -w4 processing",
            "value": 5.951,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 projected wall",
            "value": 200.049,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 CPU per pair (read for SE)",
            "value": 15.517,
            "unit": "µs"
          },
          {
            "name": "atac_hiseq_pe -w4 peak RSS",
            "value": 1218.719,
            "unit": "MB"
          },
          {
            "name": "atac_hiseq_pe -w4 fixed cost (wall)",
            "value": 0.643,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 projected CPU",
            "value": 776.545,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 wall time",
            "value": 5.429,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 CPU (user+sys)",
            "value": 19.31,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 adapter detection",
            "value": 0.438,
            "unit": "s"
          },
          {
            "name": "atac_hiseq_pe -w4 processing",
            "value": 4.903,
            "unit": "s"
          }
        ]
      }
    ]
  }
}