# M7 preregistration: complete A/B short-budget study

Frozen before observing M7 results. Configuration: `configs/m7_benchmark.json`.

## Questions and scope

Measure returned feasible cost, run-to-run variability, observed convergence, runtime and memory
for the six existing baselines: initial assignment, first relocate, first VND, Random LNS, ALNS,
and ALNS with Restricted CP-SAT Repair. Run all ten A and ten B instances with seeds
7, 42, 101, 202, 303 and a requested one-second search budget. This is a short-budget study;
10/60/300-second tiers and the complete OR-Library quality matrix are outside this execution.
The GAP track's existing exact reference checks remain separately documented.

A and B1/B2 have previously been used in development. B3–B10 are the declared held-out group;
no parameter tuning is permitted after inspecting their M7 results. Report their ALNS/restricted
paired comparison separately. Do not claim competitive performance against competition programs
or infer longer-budget behavior from this experiment.

## Methods and ablations

Keep the M5 search defaults and M6 revision-2 restricted settings. No algorithm tuning is included.
Main matrix: 20 instances × 5 seeds × 6 methods = 600 observations. Initial assignment is repeated
as a control; these repeats are not independent stochastic samples.

On A1_2, A2_3, B3 and B7, compare ALNS with each of:

1. restricted repair enabled (already in the main matrix);
2. only random destroy (remove cost/constraint-guided destroys);
3. restart disabled;
4. only greedy repair (remove regret and randomized repair).

The last three add 4 × 5 × 3 = 60 observations, for 660 total. All other parameters stay fixed.
An ablation that rarely activates its mechanism (e.g. restart under a short time limit) must be
reported as inconclusive, even if final objectives differ due to wall-clock variation.

## Execution and provenance

Commit the runner, config and protocol before freezing the manifest. Freeze the source-tree
digest, Git commit, all model/initial SHA-256 values, official checker SHA-256, exact dependency
versions, Python, OS, CPU description, CPU counts, RAM and deterministic shuffled run order.
Each observation gets a fresh worker process; only one observation runs at a time. Numerical
library thread environment variables and CP-SAT workers are fixed to one. No CPU affinity or
exclusive machine reservation is claimed.

Parsing is measured separately. Externally measure the complete solver call including state
construction, warm start, exact repair and its final oracle handoff. Record subsequent independent
validation, official checker time and whole process time separately. Existing solver deadlines
are cooperative, so initialization, an in-flight operation and verification can overshoot.
Never label a returned solution as strictly obtained within one second solely from its requested
budget. Report actual solver time and overrun counts with a preregistered 0.1-second tolerance.
Paired comparisons include an additional both-within-tolerance sensitivity summary.

A worker watchdog allows the requested budget plus 120 seconds for parsing, checking and cleanup.
A watchdog timeout, exception or checker rejection remains a failed observation; it must not be
silently retried or replaced by an initial solution. Interrupted observations with no completed
record can resume. Completed records, including failures, are immutable under normal resume.
Input, environment and source changes prevent resume in the same experiment directory.

Memory is worker-process peak working set on Windows, sampled RSS elsewhere; includes interpreter,
imports and parsing, excludes the official checker subprocess. Sampling uses a 20 ms interval.
No algorithm-only allocation peak is claimed.

## Aggregation and artifacts

For each instance/method/budget report expected and valid counts, failures and missing observations,
mean, sample standard deviation, best and worst cost, mean relative initial improvement,
time to best, actual runtime, peak memory and overruns. Feasibility denominators include failures
and missing runs. Do not substitute zero for missing costs. Pair by instance, seed and budget;
report wins/ties/losses and mean difference normalized by initial cost. Positive differences favor
the variant. No statistical significance or best-known-solution gap is claimed.

Retain complete objective components and operator statistics. The committed raw JSONL projects
convergence onto strictly improving best-so-far change points and omits full accepted-state and
weight histories. Configuration and final weights remain. Preserve checker output and assignment
hashes; assignments and temporary jobs stay under ignored `results/runs/`. Published summaries,
raw JSONL, manifest and PNG figures go under `results/m7/`, with checksums. Reports must be
regenerable from that archive without external data or rerunning solvers.

Plot mean best-so-far improvement at 51 equally spaced fractions of the requested budget using
observed trace timestamps and left-continuous carry-forward. This plot does not certify exact
deadline availability: warm-start timestamps are recorded at handoff and verification may follow.
Show quality/runtime and paired-ablation plots, plus per-operator timing CSV. CP-SAT branch counts
are distinct from heuristic move evaluations; do not use the hybrid's combined counter as a
comparable move-throughput measurement.

Any correction made after freezing must get a new manifest/version and retain the earlier
observations. Complete all planned observations and report negative findings before closing M7.
