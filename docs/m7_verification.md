# M7 verification: preregistered A/B short-budget study

## Scope and provenance

M7 evaluates the existing algorithms without post-result tuning. The protocol was frozen in
`docs/m7_protocol.md`, the matrix in `configs/m7_benchmark.json`, and the complete v2 manifest in
`results/m7/manifest.json`. It contains 20 ROADEF A/B instances, seeds 7/42/101/202/303, one
requested one-second budget, six main methods, and three additional ablations on four declared
instances: 660 observations in total.

The manifest was frozen from clean commit `ee29875c39c111c0b2a651e56450829b6f376599` at
2026-09-18T04:15:26Z. Its source digest is
`ddb2dba016f365b3853e3028416c7d0ce9cf79f5694a75466cd098b0f7d32c27`; the configuration digest
is `25e722dbab80757664f60453cd6e7e26e3fd83fa68c4b8a70531de8924451bad`; and the unmodified
official checker digest is `8a3b74c2e0be6702dad05bde170eab29c707a9af7d6ddb2fbcc00faa19444bbf`.

Environment recorded by the manifest:

- Windows 11 build 22621, Python 3.12.4;
- AMD64 Family 25 Model 68 processor, 8 physical / 16 logical CPUs;
- 16,371,519,488 bytes RAM;
- OR-Tools 9.15.6755, NumPy 2.5.3, psutil 7.2.2, Matplotlib 3.11.2;
- one numerical-library thread, one CP-SAT worker, one experiment process at a time.

The first 45 observations in `results/runs/m7-v1` are excluded. That attempt revealed that
parent-only Windows memory sampling measured the venv launcher rather than the Python worker.
Revision 2 follows Python descendants and cross-checks worker self-reported peak working set. No
method, cost parameter, instance, seed, order, or time budget changed between the attempts.
The config's `M7 v1` protocol label names the frozen study design; `m7-v2` names this measurement
implementation revision.

## Integrity and completion

The v2 runner completed with exit code 0. All 660 records have status `ok`, pass the project full
validator, and match the unmodified official checker. There are no failed, infeasible, watchdog,
or missing observations. `results/m7/records.jsonl` has 660 lines; all 11 archived artifacts listed
in `checksums.json` reproduce their SHA-256 values.
Regenerating the report directly from the committed `manifest.json` and `records.jsonl`, without
external data, reproduced the ten shared report artifacts byte for byte on the recorded Windows
environment. Git attributes preserve the audited archive bytes so its SHA-256 map survives
checkout.

Parsing, the complete solver call, post-solver verification/checking, and process time are distinct
measurements. Across all observations their mean times were 1.231, 0.987, 0.317, and 3.377 seconds;
their maxima were 16.645, 2.376, 2.936, and 22.208 seconds. Peak worker working set was 676.44 MiB
(mean 151.17 MiB). Memory includes Python, imports and parsing but excludes the checker subprocess.

## Main matrix

Improvement is `100 * (initial - returned) / initial`. Each row below contains the same 20
instances and five seeds. Means are therefore equally weighted by observation, not by absolute
cost magnitude. Sample standard deviation is across all 100 returned improvements. An overrun is
a measured complete solver call above the preregistered 1.1-second tolerance.

| Method | n | Mean improvement % | SD pp | Mean solver s | Max solver s | Overruns | Max MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| Initial | 100 | 0.000 | 0.000 | 0.014 | 0.093 | 0 | 676.44 |
| Relocate | 100 | 12.032 | 15.448 | 1.025 | 1.341 | 30 | 675.52 |
| VND | 100 | 12.008 | 15.370 | 1.032 | 1.347 | 31 | 676.20 |
| Random LNS | 100 | 5.584 | 12.636 | 1.130 | 1.726 | 37 | 676.25 |
| Adaptive ALNS | 100 | 9.126 | 16.278 | 1.266 | 2.108 | 40 | 674.40 |
| ALNS + Restricted Repair | 100 | 8.994 | 15.763 | 1.264 | 2.376 | 40 | 675.97 |

The following pairing uses identical instance, seed and budget. “Gain” is the variant's reduction
relative to ALNS, in percentage points of initial cost; positive favors the variant.

| Variant vs ALNS | Variant W/T/L | Mean gain pp | Both timely | Timely gain pp |
|---|---:|---:|---:|---:|
| Initial | 0/21/79 | -9.126 | 60 | -14.804 |
| Relocate | 72/10/18 | +2.906 | 60 | +4.938 |
| VND | 74/8/18 | +2.882 | 60 | +4.891 |
| Random LNS | 25/12/63 | -3.542 | 60 | -5.600 |
| Restricted Repair | 32/35/33 | -0.131 | 60 | -0.070 |

At this one-second scale, Relocate and VND are the strongest measured methods. ALNS improves the
initial assignment in 79/100 pairs and outperforms Random LNS in 63/100, but its setup, warm start,
adaptive selection and final oracle leave too little effective search time to beat the simpler
local methods. Restricted Repair is effectively tied with, and slightly worse on average than,
plain ALNS. This is a negative result for extra algorithmic complexity at this budget, not evidence
about longer budgets.

## A/B split and held-out result

| Group | Method | n | Mean improvement % | Overruns |
|---|---|---:|---:|---:|
| A1/A2 | Relocate | 50 | 20.847 | 0 |
| A1/A2 | VND | 50 | 20.813 | 0 |
| A1/A2 | Random LNS | 50 | 10.912 | 0 |
| A1/A2 | ALNS | 50 | 17.142 | 0 |
| A1/A2 | Restricted | 50 | 16.993 | 0 |
| B1–B10 | Relocate | 50 | 3.217 | 30 |
| B1–B10 | VND | 50 | 3.203 | 31 |
| B1–B10 | Random LNS | 50 | 0.255 | 37 |
| B1–B10 | ALNS | 50 | 1.110 | 40 |
| B1–B10 | Restricted | 50 | 0.996 | 40 |
| Held-out B3–B10 | ALNS | 40 | 0.609 | 40 |
| Held-out B3–B10 | Restricted | 40 | 0.386 | 40 |

On the declared held-out B3–B10 group, Restricted Repair has 10 wins, 22 ties and 8 losses against
ALNS, with mean gain -0.222 percentage points. All 40 pairs lack a both-within-tolerance result, so
this can only be described as returned-result behavior after a requested one-second run. It is not
a strict one-second held-out comparison. The split also shows that averages over all 20 instances
are dominated by much larger relative improvements on the A instances.

## Ablations and exact-repair telemetry

Each ablation uses A1_2, A2_3, B3 and B7 with all five seeds. Positive gain favors the variant.

| Variant vs ALNS | Variant W/T/L | Mean gain pp | Both timely | Timely gain pp |
|---|---:|---:|---:|---:|
| Restricted Repair | 7/5/8 | -0.346 | 10 | +0.238 |
| Random destroy only | 6/6/8 | -0.667 | 10 | -0.448 |
| Restart disabled | 11/7/2 | +0.386 | 10 | +0.673 |
| Greedy repair only | 12/6/2 | +0.387 | 10 | +0.709 |

The no-restart comparison is inconclusive: none of the 20 ALNS observations reached the configured
200-iteration restart interval (range 0–57), so the mechanism never activated. Its apparent gain
comes from wall-clock-dependent iteration counts rather than removing a used restart. Greedy-only
and random-only exercise real operator choices and indicate that greedy repair is preferable while
random-only destroy is harmful in this short budget. The sample is deliberately small and no
significance claim is made.

Across the 100 main Restricted runs, CP-SAT repair was called 349 times. It returned 182 verified
current-solution improvements, including 55 new global bests; 167 calls produced no accepted
improvement. Aggregate call time was 8.179 seconds (23.44 ms/call). Despite useful individual
repairs, their overall effect did not overcome scheduling and setup cost at one second.

## Separate profile

`results/m7/profile_b3.json` records a separate cProfile run of plain ALNS on B3, seed 42. The
instrumented solver took 1.358 seconds; its objective is excluded from benchmark comparisons.
Largest overlapping cumulative times were `SolutionState.__init__` (0.828 s), full `validate`
(0.799 s), relocate warm start (0.433 s), result construction/final oracle (0.339 s), and repair
(0.252 s). `machine_count` was accessed 640,142 times but accumulated only 0.123 s. The profile
supports the observed diagnosis that state construction and full-oracle work consume a material
part of a one-second B-instance run. It does not justify changing the frozen M7 implementation.

## Reproduction and artifacts

Install `.[dev,experiments]`, prepare the external files documented in `data/README.md`, and run:

```powershell
.\.venv\Scripts\python.exe -m gmrp_alns.experiments freeze `
  configs/m7_benchmark.json results/runs/m7-local `
  --checker data/raw/roadef/checker/solution_checker.exe
.\.venv\Scripts\python.exe -m gmrp_alns.experiments run `
  results/runs/m7-local --instances a1_1
.\.venv\Scripts\python.exe -m gmrp_alns.experiments run results/runs/m7-local
.\.venv\Scripts\python.exe -m gmrp_alns.experiments report `
  results/runs/m7-local results/report/m7-local
```

The checked-in archive contains:

- `manifest.json` and `records.jsonl`: frozen provenance and all projected raw observations;
- `summary.csv` / `summary.json`: per-instance/method statistics including failures and overruns;
- `paired.json`: paired ablations and held-out sensitivity counts;
- `operators.csv`: per-run operator calls, time and improvement;
- `quality_runtime.png`, `convergence.png`, `ablations.png`: generated figures;
- `profile_b3.json`: separate instrumented profile;
- `report.md`: generated full result table;
- `checksums.json`: SHA-256 integrity map for every other archived file.

## Limits

This is a single-host, one-second requested-budget study. It has no best-known-solution gaps,
competition-program comparison, hypothesis tests, or 10/60/300-second tiers. Deterministic initial
repeats are controls rather than independent stochastic evidence. Cooperative deadlines allow an
in-flight operation and final oracle to finish; 208/660 observations exceed the 1.1-second
tolerance and remain visible. The results therefore support implementation and measurement claims,
not state-of-the-art performance or longer-budget generalization.
