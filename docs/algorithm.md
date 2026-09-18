# Algorithm and implementation

## Boundaries

Input parsing constructs immutable `Instance` and assignment objects. The full validator and full
objective define correctness. `SolutionState` caches usage, transient union usage, sparse service
machine/location/neighborhood counts, moved counts and objective components. Search depends on
these layers; validators and objective functions do not depend on search.

Implemented searches stay strictly feasible. Penalty search, explicit chain-move enumeration,
machine-cluster removal and a commercial MIP backend are not implemented. Joint exact repair can
change several processes simultaneously but is not a dedicated incremental chain-move operator.

## Baselines

- Initial: evaluate the provided assignment with no optimization.
- Relocate first: visit seeded shuffled processes; evaluate destinations passing prefilters and
  accept the best improving candidate found for the first improving process.
- VND first: use relocate first, then sampled/limited swaps when relocation stalls; return to
  relocate after a successful swap.
- Random LNS: sample removed processes, rebuild them with bounded greedy or regret backtracking,
  and accept only strictly improving feasible completions.

Every accepted relocate/swap applies the same evaluated move to the cached state. Full validation
and objective recomputation check the returned assignment. Search limits are cooperative; time spent
inside initialization, a candidate scan or final validation can exceed the requested deadline.

## Adaptive ALNS

1. Construct a feasible cached state and save the initial objective.
2. Spend at most the configured fraction of total requested time on relocate warm start.
3. Select a destroy and heuristic repair with segmented roulette weights.
4. Destroy by random, high-load, resource-critical, related-service or high-move-gain selection.
5. Repair by greedy, regret or seeded randomized insertion with node/candidate/deadline limits.
6. Reject failed completions. Apply simulated annealing to feasible completions, retaining a
   separate historical best even when a worse current solution is accepted.
7. Reward new best, improving and accepted outcomes; update weights at segment boundaries.
8. After the configured stagnation interval, restart at historical best and reheat temperature.
9. Return historical best through the full correctness oracles.

Temperature is calibrated from initial cost, worsening fraction and target acceptance probability;
cooling is per iteration. Operator score is 8 for new best, 4 for current improvement, 1 for other
accepted outcomes and 0 otherwise by default. Weight updates use a reaction factor and a positive
floor. Time-budget and fixed-iteration modes differ: the former is machine-dependent; fixed seeds
and enough time for a fixed iteration count support deterministic regressions.

## Restricted CP-SAT integration

When enabled, replace the heuristic repair at iteration 1 and then every configured interval with
a restricted exact call. The selected destroy defines the joint variable processes. The local
deadline includes preparation, and only the remaining time is passed to one CP-SAT worker. Domain
truncation retains incumbents. Complete official hard constraints and costs are modeled with the
fixed complement as constants; see `mathematical_model.md`.

Only a verified strict improvement is eligible for write-back. Unknown/infeasible/non-improving
outcomes return no assignment. Exact repair is periodic, not a member of the adaptive repair pool;
it has no learned repair weight. Its destroy still receives a reward based on the result.

Per-call telemetry includes status, assignment binaries, branch/conflict counts and local timing.
In the frozen M6 implementation, the call-level `wall_time_seconds` is measured before the final
independent oracle recomputation; the enclosing ALNS operator timer includes that work. M7 uses
the enclosing external solver-call measurement for runtime comparisons. A branch is not a
heuristic move evaluation even though the inherited aggregate counter combines them.

## Experimental separation

`experiments/protocol.py` identifies configuration, inputs and ordered jobs. `runner.py` freezes
the manifest and launches serial independent workers; `worker.py` dispatches existing algorithms,
rechecks results and invokes the unmodified official checker. `report.py` checks record hashes,
materializes missing observations and produces tables/figures. This separation keeps experimental
bookkeeping out of search's inner loops.

The four M7 ablations change one mechanism at a time: restricted repair, guided destroys, restart,
and multi-strategy repair. Runtime variation and mechanism activation are inspected alongside cost;
paired differences alone do not demonstrate a causal benefit under the one-second deadline.
