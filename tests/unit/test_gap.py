from __future__ import annotations

from pathlib import Path

import pytest

from gmrp_alns.gap.checker import evaluate_assignment
from gmrp_alns.gap.exact import solve_exact
from gmrp_alns.gap.heuristics import (
    cost_greedy,
    improve_relocate,
    improve_swap,
    regret_greedy,
    repair_assignment,
)
from gmrp_alns.gap.model import GapInstance
from gmrp_alns.gap.parser import GapParseError, parse_orlib


@pytest.fixture
def gap_toy(toy_dir: Path) -> GapInstance:
    return parse_orlib(toy_dir / "gap_toy.txt", sense="minimize", reference_values=[8])[0]


def test_parse_orlib_and_reject_wrong_direction_metadata(
    toy_dir: Path, gap_toy: GapInstance
) -> None:
    assert gap_toy.summary() == {
        "name": "gap_toy-1",
        "agents": 2,
        "jobs": 4,
        "sense": "minimize",
        "reference_optimum": 8,
    }
    with pytest.raises(GapParseError, match="reference values"):
        parse_orlib(toy_dir / "gap_toy.txt", sense="minimize", reference_values=[])


def test_cp_sat_matches_known_toy_optimum(gap_toy: GapInstance) -> None:
    result = solve_exact(gap_toy, time_limit_seconds=5, seed=42)
    assert result.optimal
    assert result.objective == gap_toy.reference_optimum == 8
    assert result.assignment is not None
    assert evaluate_assignment(gap_toy, result.assignment).feasible


@pytest.mark.parametrize("constructor", [cost_greedy, regret_greedy])
def test_gap_heuristics_only_return_feasible_solutions(
    gap_toy: GapInstance, constructor: object
) -> None:
    result = constructor(gap_toy, seed=42)  # type: ignore[operator]
    assert result.assignment is not None
    assert evaluate_assignment(gap_toy, result.assignment).feasible


def test_repair_and_local_search_preserve_feasibility(gap_toy: GapInstance) -> None:
    assignment = repair_assignment(
        gap_toy,
        [0, None, None, 1],
        strategy="regret",
        seed=42,
    )
    assert assignment is not None
    relocated = improve_relocate(gap_toy, assignment)
    swapped = improve_swap(gap_toy, relocated.assignment)
    assert evaluate_assignment(gap_toy, swapped.assignment).feasible
    assert swapped.objective <= relocated.objective


def test_maximization_direction_is_not_silently_inverted(gap_toy: GapInstance) -> None:
    maximizing = GapInstance(
        costs=gap_toy.costs,
        resources=gap_toy.resources,
        capacities=gap_toy.capacities,
        sense="maximize",
        name="max-toy",
    )
    exact = solve_exact(maximizing, time_limit_seconds=5)
    assert exact.objective == 23
