# Configuration

Version-controlled GAP, GMRP, and experiment configurations explicitly record seeds, time limits,
operator limits, and acceptance criteria. Development configurations are engineering gates rather
than preregistered M7 benchmark protocols; do not silently change one after reporting its results.

- `m5_development.json`: frozen paired Random LNS versus Adaptive ALNS development comparison.
- `m6_development.json`: frozen Adaptive ALNS exact-repair enable/disable engineering ablation.
- `m7_smoke.json`: tiny end-to-end check for manifest freezing, isolated workers, official checking,
  aggregation, and plots; it is not benchmark evidence.
- `m7_benchmark.json`: preregistered M7 short-budget matrix covering 20 A/B instances, five seeds,
  six main methods, and three fixed ablations on four instances (660 observations total).
