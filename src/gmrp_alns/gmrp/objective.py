"""Full official objective recomputation for ROADEF 2012."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from gmrp_alns.gmrp.calculations import compute_usage, ensure_assignment_shape
from gmrp_alns.gmrp.model import Assignment, Instance


@dataclass(frozen=True, slots=True)
class ObjectiveBreakdown:
    load_costs: tuple[int, ...]
    balance_costs: tuple[int, ...]
    process_move_cost: int
    service_move_cost: int
    machine_move_cost: int
    weighted_load_cost: int
    weighted_balance_cost: int
    weighted_process_move_cost: int
    weighted_service_move_cost: int
    weighted_machine_move_cost: int
    total_cost: int

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation."""
        return asdict(self)


def evaluate_objective(
    instance: Instance, original: Assignment, assignment: Assignment
) -> ObjectiveBreakdown:
    """Compute every objective component from scratch using Python integers."""
    ensure_assignment_shape(instance, original, "original assignment")
    ensure_assignment_shape(instance, assignment, "assignment")
    usage = compute_usage(instance, assignment)

    load_costs = tuple(
        sum(
            max(
                0,
                usage[machine_id][resource_id]
                - instance.machines[machine_id].safety_capacities[resource_id],
            )
            for machine_id in range(instance.machine_count)
        )
        for resource_id in range(instance.resource_count)
    )
    weighted_load = sum(
        cost * resource.load_cost_weight
        for cost, resource in zip(load_costs, instance.resources, strict=True)
    )

    raw_balance_costs: list[int] = []
    for balance in instance.balance_costs:
        cost = 0
        for machine_id, machine in enumerate(instance.machines):
            available_first = (
                machine.capacities[balance.first_resource]
                - usage[machine_id][balance.first_resource]
            )
            available_second = (
                machine.capacities[balance.second_resource]
                - usage[machine_id][balance.second_resource]
            )
            cost += max(0, balance.target * available_first - available_second)
        raw_balance_costs.append(cost)
    balance_costs = tuple(raw_balance_costs)
    weighted_balance = sum(
        cost * balance.weight
        for cost, balance in zip(balance_costs, instance.balance_costs, strict=True)
    )

    moved_by_service = [0] * instance.service_count
    process_move_cost = 0
    machine_move_cost = 0
    for process_id, destination in enumerate(assignment):
        source = original[process_id]
        process = instance.processes[process_id]
        if source != destination:
            process_move_cost += process.move_cost
            moved_by_service[process.service] += 1
        machine_move_cost += instance.machines[source].move_costs[destination]
    service_move_cost = max(moved_by_service, default=0)

    weighted_process = process_move_cost * instance.process_move_cost_weight
    weighted_service = service_move_cost * instance.service_move_cost_weight
    weighted_machine = machine_move_cost * instance.machine_move_cost_weight
    total = (
        weighted_load
        + weighted_balance
        + weighted_process
        + weighted_service
        + weighted_machine
    )
    return ObjectiveBreakdown(
        load_costs=load_costs,
        balance_costs=balance_costs,
        process_move_cost=process_move_cost,
        service_move_cost=service_move_cost,
        machine_move_cost=machine_move_cost,
        weighted_load_cost=weighted_load,
        weighted_balance_cost=weighted_balance,
        weighted_process_move_cost=weighted_process,
        weighted_service_move_cost=weighted_service,
        weighted_machine_move_cost=weighted_machine,
        total_cost=total,
    )

