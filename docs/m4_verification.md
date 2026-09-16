# M4 verification record

Date: 2026-09-17

This record verifies the M4 implementation boundary: first/best relocate improvement,
relocate/swap VND, random-removal LNS with greedy/regret repair, unified limits and seeds, and
search telemetry. It is an engineering acceptance run, not a competitive or preregistered
benchmark.

## Environment and command

- Windows 11 10.0.22621, AMD64 Family 25 Model 68, 16 logical processors reported by the OS;
- Python 3.12.4;
- seed 42 and a one-second wall-clock budget per instance;
- algorithm `vnd-first`, default Top-K value 20 and at most 5,000 sampled swap pairs per scan;
- external A1/A2 files and checker remain ignored; provenance and hashes are in
  `data/manifests/`.

```bash
python scripts/verify_m4_a_set.py \
  data/raw/roadef/checker/solution_checker.exe \
  data/raw/roadef/a1 data/raw/roadef/a2 \
  --algorithm vnd-first --time-limit 1 --seed 42
```

The script parses each instance and initial assignment, runs the search, applies the full project
validator and objective oracle, writes the candidate to a temporary directory, and invokes the
unmodified official checker. Acceptance requires the checker to print that the solution is valid
and its objective to equal both project calculations.

## Recorded results

| Instance | Initial cost | Final cost | Improvement | Official checker |
|---|---:|---:|---:|---|
| a1_1 | 49,528,750 | 44,306,905 | 5,221,845 | valid, cost match |
| a1_2 | 1,061,649,570 | 892,007,067 | 169,642,503 | valid, cost match |
| a1_3 | 583,662,270 | 583,514,095 | 148,175 | valid, cost match |
| a1_4 | 632,499,600 | 414,571,767 | 217,927,833 | valid, cost match |
| a1_5 | 782,189,690 | 730,245,007 | 51,944,683 | valid, cost match |
| a2_1 | 391,189,190 | 148,432,575 | 242,756,615 | valid, cost match |
| a2_2 | 1,876,768,120 | 1,520,804,698 | 355,963,422 | valid, cost match |
| a2_3 | 2,272,487,840 | 1,927,225,557 | 345,262,283 | valid, cost match |
| a2_4 | 3,223,516,130 | 2,399,112,303 | 824,403,827 | valid, cost match |
| a2_5 | 787,355,300 | 681,449,045 | 105,906,255 | valid, cost match |

Summary: 10/10 initial assignments improved, 10/10 final assignments passed the project validator
and official checker, and 10/10 objective values agreed exactly.

## Determinism and automated checks

Seeded unit tests run both greedy- and regret-repair Random LNS twice with the same seed and fixed
iteration budget, requiring identical assignments, objectives, and iteration/cost traces. A fixed
iteration budget is the reproducibility oracle because a wall-clock cutoff can stop on a different
iteration on different machines. First/best relocate, swap-only VND escape, feasible repair,
zero-iteration behavior, and CLI assignment output are separately tested.

The final repository check for M4 reported:

- 38/38 tests passed;
- total line coverage 87%;
- Ruff passed;
- strict mypy passed for 22 source files;
- `git diff --check` passed.

Timing and time-to-best values depend on the development machine and are intentionally omitted from
the quality table. The one-second results demonstrate feasibility and initial improvement only;
they must not be presented as evidence that M4 is competitive with published solvers. Adaptive
operator selection, simulated annealing, restart, and restricted exact repair remain M5–M6 work.
