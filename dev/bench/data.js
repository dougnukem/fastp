window.BENCHMARK_DATA = {
  "lastUpdate": 1790630417670,
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
      }
    ]
  }
}