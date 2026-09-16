"""Correctness-oracle handoff shared by local search and LNS."""

from __future__ import annotations

from typing import Any

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.state import SolutionState
from gmrp_alns.gmrp.validator import validate
from gmrp_alns.search.model import OperatorStats, SearchResult, TracePoint


def build_result(
    *,
    algorithm: str,
    state: SolutionState,
    initial: Assignment,
    initial_cost: int,
    seed: int,
    time_limit_seconds: float,
    wall_time_seconds: float,
    time_to_best_seconds: float,
    iterations: int,
    candidate_evaluations: int,
    trace: list[TracePoint],
    operator_stats: dict[str, OperatorStats],
    config: dict[str, Any],
) -> SearchResult:
    """Recheck the final state with both full M1 correctness oracles."""

    instance: Instance = state.instance
    assignment = state.assignment
    report = validate(instance, initial, assignment)
    if not report.feasible:  # pragma: no cover - invariant guard
        raise AssertionError(f"search returned an infeasible assignment: {report.violations}")
    objective = evaluate_objective(instance, initial, assignment)
    if objective != state.objective:  # pragma: no cover - invariant guard
        raise AssertionError("incremental objective differs from full recomputation")
    moved_processes = sum(
        source != destination
        for source, destination in zip(initial, assignment, strict=True)
    )
    return SearchResult(
        algorithm=algorithm,
        assignment=assignment,
        objective=objective,
        initial_cost=initial_cost,
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        wall_time_seconds=wall_time_seconds,
        time_to_best_seconds=time_to_best_seconds,
        iterations=iterations,
        candidate_evaluations=candidate_evaluations,
        moved_processes=moved_processes,
        trace=tuple(trace),
        operator_stats=operator_stats,
        config=config,
    )
