from __future__ import annotations

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import evaluate_objective


def test_official_initial_cost(toy_instance: Instance, toy_original: Assignment) -> None:
    objective = evaluate_objective(toy_instance, toy_original, toy_original)
    assert objective.load_costs == (4, 130)
    assert objective.weighted_load_cost == 1700
    assert objective.balance_costs == (250,)
    assert objective.weighted_balance_cost == 2500
    assert objective.process_move_cost == 0
    assert objective.service_move_cost == 0
    assert objective.machine_move_cost == 0
    assert objective.total_cost == 4200


def test_official_optimized_cost(
    toy_instance: Instance, toy_original: Assignment, toy_solution: Assignment
) -> None:
    objective = evaluate_objective(toy_instance, toy_original, toy_solution)
    assert objective.weighted_load_cost == 400
    assert objective.weighted_balance_cost == 1600
    assert objective.process_move_cost == 101
    assert objective.service_move_cost == 1
    assert objective.machine_move_cost == 3
    assert objective.weighted_process_move_cost == 101
    assert objective.weighted_service_move_cost == 10
    assert objective.weighted_machine_move_cost == 300
    assert objective.total_cost == 2411

