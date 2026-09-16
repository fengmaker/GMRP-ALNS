from __future__ import annotations

import random
from time import perf_counter

import pytest

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.state import SolutionState
from gmrp_alns.gmrp.validator import validate
from gmrp_alns.search.acceptance import SimulatedAnnealing
from gmrp_alns.search.alns import adaptive_alns
from gmrp_alns.search.destroy import DEFAULT_DESTROY_OPERATORS, select_destroy
from gmrp_alns.search.lns import repair_removed
from gmrp_alns.search.operator_selection import AdaptiveOperatorPool


def test_simulated_annealing_accepts_and_reheats() -> None:
    acceptance = SimulatedAnnealing.from_initial_cost(
        1_000,
        target_acceptance_probability=0.5,
        initial_worsening_fraction=0.1,
        cooling_rate=0.5,
    )
    assert acceptance.accept(1_000, 900, random.Random(0))
    assert acceptance.accept(1_000, 1_100, random.Random(1))
    assert not acceptance.accept(1_000, 1_100, random.Random(2))
    initial_temperature = acceptance.temperature
    acceptance.cool()
    assert acceptance.temperature == pytest.approx(initial_temperature * 0.5)
    acceptance.reheat()
    assert acceptance.temperature == initial_temperature


def test_segmented_operator_weights_follow_reward_formula() -> None:
    pool = AdaptiveOperatorPool(("a", "b"), reaction_factor=0.5)
    pool.reward("a", 8)
    pool.reward("b", 0)
    pool.update()
    assert pool.weights() == {"a": 4.5, "b": 0.5}
    assert pool.update_counts() == {"a": 1, "b": 1}


@pytest.mark.parametrize("strategy", DEFAULT_DESTROY_OPERATORS)
def test_destroy_operators_select_unique_processes(
    toy_instance: Instance,
    toy_original: Assignment,
    strategy: str,
) -> None:
    state = SolutionState(toy_instance, toy_original, toy_original)
    first = select_destroy(  # type: ignore[arg-type]
        state,
        strategy,
        size=2,
        rng=random.Random(42),
    )
    second = select_destroy(  # type: ignore[arg-type]
        state,
        strategy,
        size=2,
        rng=random.Random(42),
    )
    assert first == second
    assert len(first) == len(set(first)) == 2
    assert all(0 <= process < toy_instance.process_count for process in first)


def test_randomized_repair_is_feasible_and_reproducible(
    toy_instance: Instance,
    toy_original: Assignment,
) -> None:
    outcomes = [
        repair_removed(
            toy_instance,
            toy_original,
            toy_original,
            (1, 2),
            strategy="randomized",
            deadline=perf_counter() + 2,
            rng=random.Random(42),
        )
        for _ in range(2)
    ]
    assert outcomes[0].assignment == outcomes[1].assignment
    assert outcomes[0].objective == outcomes[1].objective
    assert outcomes[0].assignment is not None
    assert validate(toy_instance, toy_original, outcomes[0].assignment).feasible


def test_adaptive_alns_is_reproducible_and_preserves_best(
    toy_instance: Instance,
    toy_original: Assignment,
    toy_solution: Assignment,
) -> None:
    kwargs = {
        "time_limit_seconds": 2.0,
        "seed": 42,
        "max_iterations": 30,
        "destroy_size": 2,
        "segment_length": 5,
        "restart_interval": 5,
    }
    first = adaptive_alns(toy_instance, toy_original, toy_original, **kwargs)
    second = adaptive_alns(toy_instance, toy_original, toy_original, **kwargs)
    assert first.assignment == second.assignment == toy_solution
    assert first.objective == second.objective
    first_trace = [
        (point.iteration, point.current_cost, point.best_cost, point.operator)
        for point in first.trace
    ]
    second_trace = [
        (point.iteration, point.current_cost, point.best_cost, point.operator)
        for point in second.trace
    ]
    assert first_trace == second_trace
    assert first.objective.total_cost == min(point.best_cost for point in first.trace)
    assert any(point.operator == "restart-best" for point in first.trace)
    assert len(first.operator_stats) == 9
    adaptive_stats = {
        name: stats
        for name, stats in first.operator_stats.items()
        if name.startswith(("destroy:", "repair:"))
    }
    assert all(stats.final_weight is not None for stats in adaptive_stats.values())
    assert len(first.config["weight_trace"]) == 7
    assert validate(toy_instance, toy_original, first.assignment).feasible


def test_adaptive_alns_returns_initial_best_with_zero_iterations(
    toy_instance: Instance,
    toy_original: Assignment,
) -> None:
    result = adaptive_alns(
        toy_instance,
        toy_original,
        toy_original,
        time_limit_seconds=1,
        max_iterations=0,
    )
    assert result.assignment == toy_original
    assert result.iterations == 0
    assert len(result.trace) == 1
