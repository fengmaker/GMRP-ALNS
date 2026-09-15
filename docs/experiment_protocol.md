# Experiment protocol

No solver benchmarks exist yet. Before the first benchmark, freeze an experiment configuration
that records instance identity and hash, algorithm, seed, wall-clock time limit, thread limit,
hardware, environment, Git commit, objective components, feasibility, time to best, candidate
evaluations, and operator statistics.

Development uses seed 42. Published stochastic comparisons use at least five declared seeds and
retain failures and infeasible results. Compare methods only on the same instances, hardware,
thread limit, and wall-clock budget. The official program protocol specifies a deterministic seed
parameter and a maximum five-minute real-time run per instance; modern results must state clearly
whether they reproduce or merely adapt that historical environment.

