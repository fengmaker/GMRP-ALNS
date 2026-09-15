"""Shared full-recomputation helpers used by validation and scoring."""

from __future__ import annotations

from gmrp_alns.gmrp.model import Assignment, Instance


def compute_usage(instance: Instance, assignment: Assignment) -> list[list[int]]:
    usage = [[0] * instance.resource_count for _ in range(instance.machine_count)]
    for process_id, machine_id in enumerate(assignment):
        requirements = instance.processes[process_id].requirements
        for resource_id, requirement in enumerate(requirements):
            usage[machine_id][resource_id] += requirement
    return usage


def compute_transient_usage(
    instance: Instance, original: Assignment, assignment: Assignment
) -> list[list[int]]:
    """Compute union usage: a moved process occupies each endpoint once."""
    usage = [[0] * instance.resource_count for _ in range(instance.machine_count)]
    transient_ids = [
        resource_id
        for resource_id, resource in enumerate(instance.resources)
        if resource.transient
    ]
    for process_id, destination in enumerate(assignment):
        source = original[process_id]
        requirements = instance.processes[process_id].requirements
        for resource_id in transient_ids:
            usage[destination][resource_id] += requirements[resource_id]
            if source != destination:
                usage[source][resource_id] += requirements[resource_id]
    return usage


def ensure_assignment_shape(instance: Instance, assignment: Assignment, label: str) -> None:
    if len(assignment) != instance.process_count:
        raise ValueError(
            f"{label} contains {len(assignment)} values; expected {instance.process_count}"
        )
    for process_id, machine_id in enumerate(assignment):
        if not 0 <= machine_id < instance.machine_count:
            raise ValueError(
                f"{label}[{process_id}] machine index {machine_id} is outside "
                f"[0, {instance.machine_count})"
            )

