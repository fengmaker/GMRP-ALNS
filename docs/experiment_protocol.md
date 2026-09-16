# Experiment protocol

The M2 exact reference check, M3 incremental microbenchmark, and M4 one-second A-set run are
development verification, not the preregistered M7 quality benchmark. Their commands, environment,
and timing boundaries are in `m2_m3_verification.md` and `m4_verification.md`. Before the first
solution-quality benchmark, freeze an experiment
configuration that records instance identity and hash, algorithm, seed, wall-clock time limit,
thread limit, hardware, environment, Git commit, objective components, feasibility, time to best,
candidate evaluations, and operator statistics.

Development uses seed 42. Published stochastic comparisons use at least five declared seeds and
retain failures and infeasible results. Compare methods only on the same instances, hardware,
thread limit, and wall-clock budget. The official program protocol specifies a deterministic seed
parameter and a maximum five-minute real-time run per instance; modern results must state clearly
whether they reproduce or merely adapt that historical environment.
