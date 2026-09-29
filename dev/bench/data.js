window.BENCHMARK_DATA = {
  "lastUpdate": 1790697652583,
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
      }
    ]
  }
}