from __future__ import annotations

from time import perf_counter

import pytest

from gmrp_alns.gmrp.model import (
    Assignment,
    Instance,
    Machine,
    Process,
    Resource,
    Service,
)
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.validator import validate
from gmrp_alns.search.lns import random_lns, repair_removed
from gmrp_alns.search.local_search import relocate_search, vnd_search


def _swap_improvement_instance() -> tuple[Instance, Assignment]:
    instance = Instance(
        resources=(Resource(transient=False, load_cost_weight=1),),
        machines=(
            Machine(
                neighborhood=0,
                location=0,
                capacities=(8,),
                safety_capacities=(8,),
                move_costs=(0, 0),
            ),
            Machine(
                neighborhood=0,
                location=1,
                capacities=(8,),
                safety_capacities=(4,),
                move_costs=(0, 0),
            ),
        ),
        services=(
            Service(spread_min=1, dependencies=()),
            Service(spread_min=1, dependencies=()),
        ),
        processes=(
            Process(service=0, requirements=(8,), move_cost=0),
            Process(service=1, requirements=(4,), move_cost=0),
        ),
        balance_costs=(),
        process_move_cost_weight=0,
        service_move_cost_weight=0,
        machine_move_cost_weight=0,
    )
    return instance, (1, 0)


@pytest.mark.parametrize("strategy", ["first", "best"])
def test_relocate_search_reaches_toy_solution(
    toy_instance: Instance,
    toy_original: Assignment,
    toy_solution: Assignment,
    strategy: str,
) -> None:
    result = relocate_search(
        toy_instance,
        toy_original,
        toy_original,
        strategy=strategy,  # type: ignore[arg-type]
        time_limit_seconds=2,
        seed=42,
        max_iterations=100,
    )
    assert result.assignment == toy_solution
    assert result.initial_cost == 4200
    assert result.objective.total_cost == 2411
    assert result.time_to_best_seconds <= result.wall_time_seconds
    assert [point.best_cost for point in result.trace] == sorted(
        (point.best_cost for point in result.trace), reverse=True
    )
    assert validate(toy_instance, toy_original, result.assignment).feasible


def test_vnd_uses_swap_when_relocates_are_blocked() -> None:
    instance, original = _swap_improvement_instance()
    result = vnd_search(
        instance,
        original,
        original,
        strategy="best",
        time_limit_seconds=2,
        seed=42,
        max_iterations=10,
        max_swap_candidates=10,
    )
    assert result.assignment == (0, 1)
    assert result.initial_cost == 4
    assert result.objective.total_cost == 0
    assert result.operator_stats["swap"].successes == 1
    assert validate(instance, original, result.assignment).feasible


@pytest.mark.parametrize("strategy", ["greedy", "regret"])
def test_removed_process_repair_is_feasible_and_improving(strategy: str) -> None:
    instance, original = _swap_improvement_instance()
    outcome = repair_removed(
        instance,
        original,
        original,
        (0, 1),
        strategy=strategy,  # type: ignore[arg-type]
        deadline=perf_counter() + 2,
    )
    assert outcome.assignment is not None
    assert outcome.objective is not None
    assert outcome.objective.total_cost == 0
    assert validate(instance, original, outcome.assignment).feasible


@pytest.mark.parametrize("repair", ["greedy", "regret"])
def test_random_lns_is_feasible_and_reproducible(
    toy_instance: Instance,
    toy_original: Assignment,
    repair: str,
) -> None:
    kwargs = {
        "repair": repair,
        "time_limit_seconds": 2.0,
        "seed": 42,
        "max_iterations": 20,
        "destroy_size": 2,
    }
    first = random_lns(  # type: ignore[arg-type]
        toy_instance,
        toy_original,
        toy_original,
        **kwargs,
    )
    second = random_lns(  # type: ignore[arg-type]
        toy_instance,
        toy_original,
        toy_original,
        **kwargs,
    )
    assert first.assignment == second.assignment
    assert first.objective == second.objective
    assert [(point.iteration, point.best_cost) for point in first.trace] == [
        (point.iteration, point.best_cost) for point in second.trace
    ]
    assert first.objective.total_cost == 2411
    assert validate(toy_instance, toy_original, first.assignment).feasible
    assert evaluate_objective(toy_instance, toy_original, first.assignment) == first.objective


def test_zero_iteration_limit_returns_initial_assignment(
    toy_instance: Instance, toy_original: Assignment
) -> None:
    result = vnd_search(
        toy_instance,
        toy_original,
        toy_original,
        time_limit_seconds=1,
        max_iterations=0,
    )
    assert result.assignment == toy_original
    assert result.iterations == 0
    assert len(result.trace) == 1
