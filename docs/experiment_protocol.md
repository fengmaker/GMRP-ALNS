# Experiment protocol

The M2 exact reference check, M3 incremental microbenchmark, M4 one-second A-set run, M5 paired
development gate, and M6 exact-repair ablation are development verification, not the preregistered
M7 quality benchmark. Their commands, environment, and timing boundaries are in
`m2_m3_verification.md`, `m4_verification.md`, `m5_verification.md`, and `m6_verification.md`.
M7's first solution-quality benchmark was frozen before observing its results. The complete
preregistration, including the declared held-out group and revision history, is in
`m7_protocol.md`; its version-controlled configuration is `configs/m7_benchmark.json`. The frozen
manifest records instance/checker hashes, algorithm, seed, requested wall-clock budget, thread
limit, hardware, environment, Git commit, dependency versions, objective components, feasibility,
time to best, candidate evaluations, and operator statistics.

Development uses seed 42. Published stochastic comparisons use at least five declared seeds and
retain failures and infeasible results. Compare methods only on the same instances, hardware,
thread limit, and wall-clock budget. The official program protocol specifies a deterministic seed
parameter and a maximum five-minute real-time run per instance; modern results must state clearly
whether they reproduce or merely adapt that historical environment.

Restricted Repair comparisons must additionally retain the invocation interval, candidate-machine
limit, assignment-variable limit, local solver budget, solver worker count, per-call status and
time, and the number of verified current-solution improvements. The disabled and enabled methods
must share the same total search budget; local CP-SAT time is not added on top.

Each M7 observation runs in a fresh serial worker process. The raw record distinguishes parsing,
the complete solver call, independent full validation, official checker time, and whole-process
time. Because deadlines are cooperative, returned observations remain in the dataset when their
measured solver call exceeds the requested budget; a preregistered 0.1-second tolerance and a
same-pair sensitivity summary expose those overruns. Failures and missing runs are never replaced
with initial solutions. Peak memory is the worker-process high-water working set on Windows (RSS
sampling elsewhere) and excludes the official checker subprocess.

The completed v2 matrix and its interpretation are archived in `results/m7/` and
`m7_verification.md`. The report retains all 660 valid records and 208 measured solver-call
overruns; the excluded v1 attempt and the reason for rerunning it are disclosed in both the
preregistration and verification record.
