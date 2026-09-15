# M1 verification record

Verification was performed on 2026-09-15 with Python 3.12.4 and the official checker compiled
from the source files recorded in `data/manifests/roadef_checker.json`. Downloaded inputs are
ignored; their source URLs, byte sizes, timestamps, and SHA-256 digests are committed under
`data/manifests/`.

All ten official A1/A2 initial assignments passed the independent validator. Full objective
values agreed exactly with the unmodified official checker:

| Instance | Independent evaluator | Official checker |
|---|---:|---:|
| a1_1 | 49,528,750 | 49,528,750 |
| a1_2 | 1,061,649,570 | 1,061,649,570 |
| a1_3 | 583,662,270 | 583,662,270 |
| a1_4 | 632,499,600 | 632,499,600 |
| a1_5 | 782,189,690 | 782,189,690 |
| a2_1 | 391,189,190 | 391,189,190 |
| a2_2 | 1,876,768,120 | 1,876,768,120 |
| a2_3 | 2,272,487,840 | 2,272,487,840 |
| a2_4 | 3,223,516,130 | 3,223,516,130 |
| a2_5 | 787,355,300 | 787,355,300 |

The committed test suite separately covers malformed input, assignment round trips, all five
hard-constraint families, transient union semantics, both official toy objective values, and CLI
exit/output behavior. At this milestone: 19 tests pass, Ruff passes, and strict mypy passes.

This record validates parsing and full evaluation only. It does not constitute a solver-quality
benchmark, and no optimization claim is made.
