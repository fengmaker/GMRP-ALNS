"""Adaptive large-neighborhood search for strict-feasible GMRP solutions."""

from __future__ import annotations

import random
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from gmrp_alns.exact.restricted_repair import restricted_cpsat_repair
from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import ObjectiveBreakdown, evaluate_objective
from gmrp_alns.gmrp.state import SolutionState
from gmrp_alns.search.acceptance import SimulatedAnnealing
from gmrp_alns.search.common import build_result
from gmrp_alns.search.destroy import (
    DEFAULT_DESTROY_OPERATORS,
    DestroyStrategy,
    select_destroy,
)
from gmrp_alns.search.lns import RepairStrategy, repair_removed
from gmrp_alns.search.local_search import relocate_search
from gmrp_alns.search.model import OperatorStats, SearchResult, TracePoint
from gmrp_alns.search.operator_selection import AdaptiveOperatorPool

DEFAULT_REPAIR_OPERATORS: tuple[RepairStrategy, ...] = (
    "greedy",
    "regret",
    "randomized",
)


def _objective_difference(
    before: ObjectiveBreakdown, after: ObjectiveBreakdown
) -> dict[str, Any]:
    before_values = before.as_dict()
    after_values = after.as_dict()
    difference: dict[str, Any] = {}
    for name, after_value in after_values.items():
        before_value = before_values[name]
        if isinstance(after_value, tuple) and isinstance(before_value, tuple):
            difference[name] = [
                right - left
                for left, right in zip(before_value, after_value, strict=True)
            ]
        elif isinstance(after_value, int) and isinstance(before_value, int):
            difference[name] = after_value - before_value
    return difference


@dataclass(slots=True)
class _MutableStats:
    calls: int = 0
    accepted: int = 0
    new_best: int = 0
    failures: int = 0
    candidate_evaluations: int = 0
    total_improvement: int = 0
    wall_time_seconds: float = 0.0

    def freeze(
        self, *, final_weight: float | None, weight_updates: int
    ) -> OperatorStats:
        return OperatorStats(
            calls=self.calls,
            successes=self.accepted,
            candidate_evaluations=self.candidate_evaluations,
            total_improvement=self.total_improvement,
            wall_time_seconds=self.wall_time_seconds,
            accepted=self.accepted,
            new_best=self.new_best,
            failures=self.failures,
            final_weight=final_weight,
            weight_updates=weight_updates,
        )


def _validate_parameters(
    *,
    time_limit_seconds: float,
    max_iterations: int | None,
    destroy_size: int,
    repair_top_k: int,
    repair_node_limit: int,
    segment_length: int,
    reaction_factor: float,
    restart_interval: int,
    warm_start_fraction: float,
    restricted_repair_interval: int,
    restricted_repair_time_limit_seconds: float,
    restricted_repair_candidate_machines: int,
    restricted_repair_variable_limit: int,
    destroy_operators: tuple[DestroyStrategy, ...],
    repair_operators: tuple[RepairStrategy, ...],
) -> None:
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    if max_iterations is not None and max_iterations < 0:
        raise ValueError("max_iterations must be non-negative")
    if destroy_size <= 0 or repair_top_k <= 0 or repair_node_limit <= 0:
        raise ValueError("destroy and repair limits must be positive")
    if segment_length <= 0:
        raise ValueError("segment_length must be positive")
    if not 0 < reaction_factor <= 1:
        raise ValueError("reaction_factor must be in (0, 1]")
    if restart_interval < 0:
        raise ValueError("restart_interval must be non-negative")
    if not 0 <= warm_start_fraction < 1:
        raise ValueError("warm_start_fraction must be in [0, 1)")
    if restricted_repair_interval < 0:
        raise ValueError("restricted_repair_interval must be non-negative")
    if restricted_repair_time_limit_seconds <= 0:
        raise ValueError("restricted_repair_time_limit_seconds must be positive")
    if restricted_repair_candidate_machines <= 0:
        raise ValueError("restricted_repair_candidate_machines must be positive")
    if restricted_repair_variable_limit <= 0:
        raise ValueError("restricted_repair_variable_limit must be positive")
    if not destroy_operators or len(set(destroy_operators)) != len(destroy_operators):
        raise ValueError("destroy_operators must be non-empty and unique")
    if not repair_operators or len(set(repair_operators)) != len(repair_operators):
        raise ValueError("repair_operators must be non-empty and unique")
    if any(name not in DEFAULT_DESTROY_OPERATORS for name in destroy_operators):
        raise ValueError("destroy_operators contains an unknown operator")
    if any(name not in DEFAULT_REPAIR_OPERATORS for name in repair_operators):
        raise ValueError("repair_operators contains an unknown operator")


def adaptive_alns(
    instance: Instance,
    original: Assignment,
    assignment: Assignment,
    *,
    time_limit_seconds: float = 60.0,
    seed: int = 0,
    max_iterations: int | None = None,
    destroy_size: int = 10,
    repair_top_k: int = 10,
    repair_node_limit: int = 10_000,
    destroy_operators: tuple[DestroyStrategy, ...] = DEFAULT_DESTROY_OPERATORS,
    repair_operators: tuple[RepairStrategy, ...] = DEFAULT_REPAIR_OPERATORS,
    segment_length: int = 25,
    reaction_factor: float = 0.2,
    score_new_best: float = 8.0,
    score_improving: float = 4.0,
    score_accepted: float = 1.0,
    target_acceptance_probability: float = 0.5,
    initial_worsening_fraction: float = 0.01,
    cooling_rate: float = 0.995,
    restart_interval: int = 200,
    warm_start_fraction: float = 0.2,
    restricted_repair_interval: int = 0,
    restricted_repair_time_limit_seconds: float = 0.1,
    restricted_repair_candidate_machines: int = 10,
    restricted_repair_variable_limit: int = 200,
) -> SearchResult:
    """Run strict-feasible Adaptive ALNS, optionally with periodic exact repair."""

    _validate_parameters(
        time_limit_seconds=time_limit_seconds,
        max_iterations=max_iterations,
        destroy_size=destroy_size,
        repair_top_k=repair_top_k,
        repair_node_limit=repair_node_limit,
        segment_length=segment_length,
        reaction_factor=reaction_factor,
        restart_interval=restart_interval,
        warm_start_fraction=warm_start_fraction,
        restricted_repair_interval=restricted_repair_interval,
        restricted_repair_time_limit_seconds=restricted_repair_time_limit_seconds,
        restricted_repair_candidate_machines=restricted_repair_candidate_machines,
        restricted_repair_variable_limit=restricted_repair_variable_limit,
        destroy_operators=destroy_operators,
        repair_operators=repair_operators,
    )
    if min(score_new_best, score_improving, score_accepted) < 0:
        raise ValueError("operator scores must be non-negative")

    started = perf_counter()
    deadline = started + time_limit_seconds
    rng = random.Random(seed)
    current = SolutionState(instance, original, assignment)
    initial_cost = evaluate_objective(instance, original, assignment).total_cost
    time_to_best = 0.0
    trace = [
        TracePoint(
            0.0,
            0,
            current.total_cost,
            current.total_cost,
            "initial",
            current.objective,
        )
    ]
    warm_start_stats = _MutableStats()
    warm_start_iterations = 0
    warm_start_evaluations = 0
    if warm_start_fraction > 0 and max_iterations != 0 and perf_counter() < deadline:
        objective_before_warm_start = current.objective
        warm_start_stats.calls = 1
        warm_budget = min(
            time_limit_seconds * warm_start_fraction,
            max(1e-9, deadline - perf_counter()),
        )
        warm_result = relocate_search(
            instance,
            original,
            current.assignment,
            strategy="first",
            time_limit_seconds=warm_budget,
            seed=seed,
        )
        warm_start_stats.wall_time_seconds = warm_result.wall_time_seconds
        warm_start_stats.candidate_evaluations = warm_result.candidate_evaluations
        warm_start_iterations = warm_result.iterations
        warm_start_evaluations = warm_result.candidate_evaluations
        improvement = initial_cost - warm_result.objective.total_cost
        if improvement > 0:
            warm_start_stats.accepted = 1
            warm_start_stats.new_best = 1
            warm_start_stats.total_improvement = improvement
            current = SolutionState(instance, original, warm_result.assignment)
            time_to_best = perf_counter() - started
            trace.append(
                TracePoint(
                    time_to_best,
                    0,
                    current.total_cost,
                    current.total_cost,
                    "warm-start-relocate",
                    current.objective,
                    _objective_difference(objective_before_warm_start, current.objective),
                )
            )

    best_assignment = current.assignment
    best_objective = current.objective

    annealing = SimulatedAnnealing.from_initial_cost(
        initial_cost,
        target_acceptance_probability=target_acceptance_probability,
        initial_worsening_fraction=initial_worsening_fraction,
        cooling_rate=cooling_rate,
    )
    destroy_pool = AdaptiveOperatorPool(
        tuple(destroy_operators),
        reaction_factor=reaction_factor,
    )
    repair_pool = AdaptiveOperatorPool(
        tuple(repair_operators),
        reaction_factor=reaction_factor,
    )
    destroy_stats = {name: _MutableStats() for name in destroy_operators}
    repair_stats = {name: _MutableStats() for name in repair_operators}
    restricted_stats = _MutableStats()
    restricted_trace: list[dict[str, Any]] = []
    weight_trace: list[dict[str, Any]] = [
        {
            "iteration": 0,
            "destroy": destroy_pool.weights(),
            "repair": repair_pool.weights(),
        }
    ]
    iterations = 0
    candidate_evaluations = warm_start_evaluations
    accepted_worsening = 0
    restarts = 0
    last_best_iteration = 0
    last_restart_iteration = 0

    def update_weights() -> None:
        destroy_pool.update()
        repair_pool.update()
        weight_trace.append(
            {
                "iteration": iterations,
                "destroy": destroy_pool.weights(),
                "repair": repair_pool.weights(),
            }
        )

    while perf_counter() < deadline and (
        max_iterations is None or iterations < max_iterations
    ):
        iterations += 1
        destroy_name = cast(DestroyStrategy, destroy_pool.select(rng))
        use_restricted = bool(
            restricted_repair_interval
            and (iterations - 1) % restricted_repair_interval == 0
        )
        repair_name = (
            "restricted-cpsat"
            if use_restricted
            else cast(RepairStrategy, repair_pool.select(rng))
        )
        selected_destroy_stats = destroy_stats[destroy_name]
        selected_repair_stats = (
            restricted_stats if use_restricted else repair_stats[cast(RepairStrategy, repair_name)]
        )
        selected_destroy_stats.calls += 1
        selected_repair_stats.calls += 1

        destroy_started = perf_counter()
        removed = select_destroy(
            current,
            destroy_name,
            size=destroy_size,
            rng=rng,
        )
        selected_destroy_stats.wall_time_seconds += perf_counter() - destroy_started

        repair_started = perf_counter()
        if use_restricted:
            exact_outcome = restricted_cpsat_repair(
                instance,
                original,
                current.assignment,
                removed,
                deadline=deadline,
                time_limit_seconds=restricted_repair_time_limit_seconds,
                candidate_machine_limit=restricted_repair_candidate_machines,
                variable_limit=restricted_repair_variable_limit,
                seed=seed + iterations,
            )
            outcome_assignment = exact_outcome.assignment
            outcome_objective = exact_outcome.objective
            outcome_evaluations = exact_outcome.branches
            restricted_trace.append(
                {
                    "iteration": iterations,
                    "status": exact_outcome.status,
                    "improved": exact_outcome.improved,
                    "assignment_variables": exact_outcome.assignment_variables,
                    "branches": exact_outcome.branches,
                    "conflicts": exact_outcome.conflicts,
                    "best_bound": exact_outcome.best_bound,
                    "solver_time_limit_seconds": exact_outcome.solver_time_limit_seconds,
                    "wall_time_seconds": exact_outcome.wall_time_seconds,
                }
            )
        else:
            heuristic_outcome = repair_removed(
                instance,
                original,
                current.assignment,
                removed,
                strategy=cast(RepairStrategy, repair_name),
                deadline=deadline,
                top_k=repair_top_k,
                node_limit=repair_node_limit,
                rng=rng if repair_name == "randomized" else None,
            )
            outcome_assignment = heuristic_outcome.assignment
            outcome_objective = heuristic_outcome.objective
            outcome_evaluations = heuristic_outcome.candidate_evaluations
        selected_repair_stats.wall_time_seconds += perf_counter() - repair_started
        selected_repair_stats.candidate_evaluations += outcome_evaluations
        candidate_evaluations += outcome_evaluations

        reward = 0.0
        if outcome_assignment is None or outcome_objective is None:
            selected_destroy_stats.failures += 1
            selected_repair_stats.failures += 1
        else:
            previous_cost = current.total_cost
            previous_objective = current.objective
            candidate_cost = outcome_objective.total_cost
            accepted = annealing.accept(previous_cost, candidate_cost, rng)
            if accepted:
                selected_destroy_stats.accepted += 1
                selected_repair_stats.accepted += 1
                improvement = max(0, previous_cost - candidate_cost)
                selected_destroy_stats.total_improvement += improvement
                selected_repair_stats.total_improvement += improvement
                if candidate_cost > previous_cost:
                    accepted_worsening += 1
                current = SolutionState(instance, original, outcome_assignment)
                if candidate_cost < best_objective.total_cost:
                    best_assignment = outcome_assignment
                    best_objective = outcome_objective
                    time_to_best = perf_counter() - started
                    last_best_iteration = iterations
                    selected_destroy_stats.new_best += 1
                    selected_repair_stats.new_best += 1
                    reward = score_new_best
                elif candidate_cost < previous_cost:
                    reward = score_improving
                else:
                    reward = score_accepted
                trace.append(
                    TracePoint(
                        perf_counter() - started,
                        iterations,
                        current.total_cost,
                        best_objective.total_cost,
                        f"{destroy_name}+{repair_name}",
                        current.objective,
                        _objective_difference(previous_objective, current.objective),
                    )
                )

        destroy_pool.reward(destroy_name, reward)
        if not use_restricted:
            repair_pool.reward(cast(RepairStrategy, repair_name), reward)
        annealing.cool()

        if iterations % segment_length == 0:
            update_weights()

        stagnation_origin = max(last_best_iteration, last_restart_iteration)
        if restart_interval and iterations - stagnation_origin >= restart_interval:
            objective_before_restart = current.objective
            current = SolutionState(instance, original, best_assignment)
            annealing.reheat()
            restarts += 1
            last_restart_iteration = iterations
            trace.append(
                TracePoint(
                    perf_counter() - started,
                    iterations,
                    current.total_cost,
                    best_objective.total_cost,
                    "restart-best",
                    current.objective,
                    _objective_difference(objective_before_restart, current.objective),
                )
            )

    if iterations % segment_length:
        update_weights()

    final_destroy_weights = destroy_pool.weights()
    final_repair_weights = repair_pool.weights()
    destroy_updates = destroy_pool.update_counts()
    repair_updates = repair_pool.update_counts()
    operator_stats = {
        **{
            f"destroy:{name}": stats.freeze(
                final_weight=final_destroy_weights[name],
                weight_updates=destroy_updates[name],
            )
            for name, stats in destroy_stats.items()
        },
        **{
            f"repair:{name}": stats.freeze(
                final_weight=final_repair_weights[name],
                weight_updates=repair_updates[name],
            )
            for name, stats in repair_stats.items()
        },
    }
    if warm_start_fraction > 0:
        operator_stats["warm-start:relocate"] = warm_start_stats.freeze(
            final_weight=None,
            weight_updates=0,
        )
    if restricted_repair_interval:
        operator_stats["repair:restricted-cpsat"] = restricted_stats.freeze(
            final_weight=None,
            weight_updates=0,
        )
    best_state = SolutionState(instance, original, best_assignment)
    wall_time = perf_counter() - started
    return build_result(
        algorithm=(
            "adaptive-alns-restricted"
            if restricted_repair_interval
            else "adaptive-alns"
        ),
        state=best_state,
        initial=original,
        initial_cost=initial_cost,
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        wall_time_seconds=wall_time,
        time_to_best_seconds=time_to_best,
        iterations=iterations,
        candidate_evaluations=candidate_evaluations,
        trace=trace,
        operator_stats=operator_stats,
        config={
            "max_iterations": max_iterations,
            "destroy_size": destroy_size,
            "repair_top_k": repair_top_k,
            "repair_node_limit": repair_node_limit,
            "destroy_operators": list(destroy_operators),
            "repair_operators": list(repair_operators),
            "segment_length": segment_length,
            "reaction_factor": reaction_factor,
            "scores": {
                "new_best": score_new_best,
                "improving": score_improving,
                "accepted": score_accepted,
                "rejected_or_failed": 0.0,
            },
            "acceptance": {
                "name": "simulated-annealing",
                "target_initial_probability": target_acceptance_probability,
                "initial_worsening_fraction": initial_worsening_fraction,
                "initial_temperature": annealing.initial_temperature,
                "final_temperature": annealing.temperature,
                "cooling_rate": cooling_rate,
                "accepted_worsening": accepted_worsening,
            },
            "restart_interval": restart_interval,
            "restarts": restarts,
            "weight_trace": weight_trace,
            "strict_feasible": True,
            "warm_start": {
                "algorithm": "relocate-first",
                "fraction": warm_start_fraction,
                "iterations": warm_start_iterations,
                "candidate_evaluations": warm_start_evaluations,
            },
            "restricted_repair": {
                "enabled": bool(restricted_repair_interval),
                "interval": restricted_repair_interval,
                "time_limit_seconds": restricted_repair_time_limit_seconds,
                "candidate_machine_limit": restricted_repair_candidate_machines,
                "variable_limit": restricted_repair_variable_limit,
                "calls": restricted_trace,
            },
        },
    )
