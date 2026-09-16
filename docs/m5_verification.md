# M5 verification record

Date: 2026-09-17

This is an engineering acceptance record for Adaptive ALNS, not the preregistered M7 benchmark.
External A/B instances and the checker remain ignored; their URLs and SHA-256 hashes are recorded
under `data/manifests/`.

## Implemented boundary

- destroy: random, high-load, resource-critical, related-service, and high-move-gain removal;
- repair: greedy, regret, and seeded randomized strict-feasible repair;
- simulated annealing fitted from the initial objective and target acceptance probability;
- segmented roulette selection with reaction-weight updates and complete weight history;
- in-budget relocate warm start, stagnation restart to the historical best, and final best-solution
  protection;
- accepted/current/best costs, objective components, calls, failures, candidate counts, timing,
  improvements, final weights, and weight-update counts in JSON.

Penalty Search is not silently approximated: all M5 operators remain in `strict_feasible` mode.
Explicit constraint softening and dynamic penalties remain a possible later extension, while M6
implements restricted exact repair.

## Frozen paired development gate

`configs/m5_development.json` fixes A1_1, A1_2, and A1_4; seeds 7, 42, and 101; and one second per
method. Random LNS with greedy repair is compared against Adaptive ALNS under the same total
wall-clock budget. The gate requires at least six Adaptive ALNS wins out of nine pairs and a lower
summed objective.

The first no-warm-start revision produced 4/9 wins and did not pass. Revision 2 retained the same
instances, seeds, total time, and acceptance rule, but added a 20% in-budget relocate warm start.
This tuning history is recorded because the set is a development set, not unbiased final evidence.

```bash
python scripts/verify_m5_development.py \
  configs/m5_development.json \
  data/raw/roadef/checker/solution_checker.exe \
  data/raw/roadef
```

| Instance | Seed | Random LNS | Adaptive ALNS | Adaptive difference |
|---|---:|---:|---:|---:|
| a1_1 | 7 | 44,306,703 | 44,306,703 | 0 |
| a1_1 | 42 | 44,307,410 | 44,306,905 | 505 |
| a1_1 | 101 | 44,306,501 | 44,307,511 | -1,010 |
| a1_2 | 7 | 861,202,738 | 902,787,534 | -41,584,796 |
| a1_2 | 42 | 950,295,059 | 909,585,348 | 40,709,711 |
| a1_2 | 101 | 931,382,047 | 889,791,660 | 41,590,387 |
| a1_4 | 7 | 632,499,600 | 463,690,956 | 168,808,644 |
| a1_4 | 42 | 632,499,600 | 508,241,775 | 124,257,825 |
| a1_4 | 101 | 627,068,376 | 544,801,667 | 82,266,709 |

Adaptive ALNS won 6/9 pairs, tied one, lost two, and reduced the summed objective by 416,047,975.
All 18 outputs passed the unmodified official checker with exact cost agreement.

## A/B feasibility gate

Seed 42 and a one-second budget were used. Adaptive ALNS improved all ten A1/A2 initial solutions;
all ten outputs passed the project oracle and official checker. The final costs were:

| A instance | Final cost | A instance | Final cost |
|---|---:|---|---:|
| a1_1 | 44,306,905 | a2_1 | 98,256,838 |
| a1_2 | 909,384,264 | a2_2 | 1,633,385,366 |
| a1_3 | 583,514,196 | a2_3 | 2,072,111,349 |
| a1_4 | 506,755,491 | a2_4 | 2,793,203,393 |
| a1_5 | 727,642,850 | a2_5 | 742,441,810 |

The B-set gate deliberately uses B1 and B2 as declared representative large instances; it does
not claim an all-B benchmark:

| Instance | Initial cost | Final cost | Improvement | Official checker |
|---|---:|---:|---:|---|
| b_1 | 7,644,173,180 | 7,343,295,478 | 300,877,702 | valid, cost match |
| b_2 | 5,181,493,830 | 5,079,694,133 | 101,799,697 | valid, cost match |

The complete ten-instance B input set was downloaded and hashed, but the remaining B instances are
reserved for M7's frozen experiment matrix. No claim is made about their M5 solution quality.

## Automated verification and limits

- 49/49 tests passed with 87% total line coverage;
- Ruff passed;
- strict mypy passed for 26 source files;
- `git diff --check` passed;
- fixed-iteration tests require identical assignments, objectives, operator sequences, and weight
  history for the same seed.

One-second wall-clock results are machine- and scheduling-dependent. The paired development set was
used to tune the warm start, so these numbers cannot be promoted to a generalization claim. M7 must
freeze separate evaluation instances, multiple seeds, hardware, dependencies, and the exact commit
before producing reportable quality comparisons.
