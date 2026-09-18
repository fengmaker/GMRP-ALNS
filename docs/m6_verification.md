# M6 verification record

Date: 2026-09-18

This is an engineering acceptance record for Restricted CP-SAT Repair, not the preregistered M7
benchmark. External A/B instances and the official checker remain ignored; their provenance and
SHA-256 hashes are recorded under `data/manifests/`.

## Implemented boundary

`src/gmrp_alns/exact/restricted_repair.py` fixes every process outside the destroyed neighborhood
and creates Boolean variables only for bounded process–candidate-machine pairs. The incumbent
machine is always retained, so domain pruning cannot remove the current feasible assignment.

The local model includes:

- ordinary and transient resource capacity;
- service conflict, location spread, and neighborhood dependency;
- weighted load, balance, process move, service move, and machine move costs;
- one deterministic CP-SAT worker and an incumbent assignment hint;
- a candidate-machine limit, assignment-variable limit, and local deadline that includes model
  preparation before the remaining budget is passed to CP-SAT.

A solver candidate is never trusted directly. It is rechecked by the independent full Validator
and Objective, and it is returned only when it strictly improves the incumbent. Unknown, timeout,
infeasible, non-improving, over-limit, and oracle-rejected attempts return no assignment, leaving
the ALNS state unchanged.

Adaptive ALNS can enable the exact operator periodically through
`adaptive-alns-restricted`. JSON contains aggregate operator statistics plus one record per call:
iteration, status, improvement flag, assignment variables, branches, conflicts, bound, remaining
solver budget, and wall time.

## Correctness and safety tests

The toy tests enumerate all seven non-empty subsets of its three processes and every assignment of
each subset while fixing the complement. Restricted CP-SAT matches the brute-force feasible optimum
for every neighborhood. Separate tests cover the variable-limit fallback, an already expired
deadline, ALNS integration, and CLI telemetry. Final output still passes the shared full-oracle
handoff.

The recorded quality checks are:

- 55/55 tests passed with 88% total line coverage;
- Ruff passed;
- strict mypy passed for 28 source files;
- `git diff --check` passed.

## Frozen enable/disable ablation

`configs/m6_development.json` fixes A1_1, A1_2, and A1_4; seeds 7, 42, and 101; and one second per
method. Both sides use the same M5 Adaptive ALNS settings. The hybrid additionally invokes exact
repair on iteration 1 and then every 10 iterations, with ten candidate machines per process, 100
assignment variables, a 0.05-second per-call budget, and one solver worker.

A preliminary pre-freeze smoke called exact repair only on exact interval multiples. Very slow
A1_4 runs sometimes completed fewer than ten ALNS iterations and therefore made no exact call.
Revision 2 moved the first call to iteration 1 while retaining the interval and all other limits.
This adjustment is recorded because this remains a development configuration.

```bash
python scripts/verify_m6_development.py \
  configs/m6_development.json \
  data/raw/roadef/checker/solution_checker.exe \
  data/raw/roadef
```

| Instance | Seed | Adaptive ALNS | + Restricted CP-SAT | Hybrid difference | Exact calls | Exact improvements |
|---|---:|---:|---:|---:|---:|---:|
| a1_1 | 7 | 44,306,703 | 44,306,703 | 0 | 39 | 24 |
| a1_1 | 42 | 44,306,905 | 44,306,905 | 0 | 36 | 17 |
| a1_1 | 101 | 44,307,511 | 44,307,511 | 0 | 43 | 29 |
| a1_2 | 7 | 893,734,232 | 888,837,709 | 4,896,523 | 5 | 2 |
| a1_2 | 42 | 904,217,292 | 911,474,181 | -7,256,889 | 4 | 4 |
| a1_2 | 101 | 891,359,971 | 889,293,548 | 2,066,423 | 5 | 4 |
| a1_4 | 7 | 465,863,028 | 459,867,225 | 5,995,803 | 1 | 1 |
| a1_4 | 42 | 509,561,990 | 499,706,746 | 9,855,244 | 1 | 1 |
| a1_4 | 101 | 546,447,929 | 539,812,811 | 6,635,118 | 1 | 1 |

The hybrid won five pairs, tied three, lost one, and reduced the summed objective by 22,192,222.
There were 135 restricted calls, of which 83 strictly improved the current solution. Every call
stayed within 100 assignment variables and its CP-SAT budget never exceeded 0.05 seconds; the
verification script also allows at most 0.05 seconds of model-building and timer overhead beyond
that local budget. All 18 final assignments passed the unmodified official checker with exact cost
agreement.

## Large-instance safety smoke

One one-second B1 run used seed 42, exact repair every iteration, the same 100-variable and
0.05-second local limits, and produced 11 restricted calls. The final cost was 6,935,472,463 and
matched the official checker. This single wall-clock run is only a failure-safety and integration
smoke test; it is not evidence of B-set quality or of a general performance gain.

## Interpretation and limits

The ablation demonstrates that the exact operator is bounded, observable, safe to fail, capable of
improving the current solution, and compatible with the official checker. It does not establish
H4 as a general conclusion. One-second wall-clock results vary with scheduling, the development
instances influenced the integration policy, and the hybrid spends time on exact models that can
reduce the number of heuristic iterations. M7 must freeze independent A/B evaluation instances,
at least five seeds, longer time tiers, hardware and dependency versions, and the exact commit
before making reportable quality claims.
