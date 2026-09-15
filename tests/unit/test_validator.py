from __future__ import annotations

import pytest

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.validator import validate


def constraints_for(
    instance: Instance, original: Assignment, candidate: Assignment
) -> set[str]:
    return {item.constraint for item in validate(instance, original, candidate).violations}


def test_official_example_solutions_are_feasible(
    toy_instance: Instance, toy_original: Assignment, toy_solution: Assignment
) -> None:
    assert validate(toy_instance, toy_original, toy_original).feasible
    assert validate(toy_instance, toy_original, toy_solution).feasible


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ((0, 3, 3), "capacity"),
        ((0, 0, 0), "conflict"),
        ((0, 1, 0), "spread"),
        ((0, 1, 2), "dependency"),
        ((1, 3, 1), "transient_capacity"),
    ],
)
def test_each_hard_constraint_family(
    toy_instance: Instance,
    toy_original: Assignment,
    candidate: Assignment,
    expected: str,
) -> None:
    assert expected in constraints_for(toy_instance, toy_original, candidate)


def test_transient_process_staying_put_is_not_double_counted(
    toy_instance: Instance, toy_original: Assignment
) -> None:
    report = validate(toy_instance, toy_original, toy_original)
    assert "transient_capacity" not in {v.constraint for v in report.violations}

