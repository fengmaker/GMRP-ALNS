"""Independent full hard-constraint validator."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from gmrp_alns.gmrp.calculations import (
    compute_transient_usage,
    compute_usage,
    ensure_assignment_shape,
)
from gmrp_alns.gmrp.model import Assignment, Instance


@dataclass(frozen=True, slots=True)
class Violation:
    constraint: str
    message: str
    process: int | None = None
    machine: int | None = None
    resource: int | None = None
    service: int | None = None
    neighborhood: int | None = None
    location: int | None = None
    actual: int | None = None
    limit: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True, slots=True)
class ValidationReport:
    feasible: bool
    violations: tuple[Violation, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "feasible": self.feasible,
            "violation_count": len(self.violations),
            "violations": [violation.as_dict() for violation in self.violations],
        }


def validate(
    instance: Instance, original: Assignment, assignment: Assignment
) -> ValidationReport:
    """Check all five official hard-constraint families from scratch."""
    ensure_assignment_shape(instance, original, "original assignment")
    ensure_assignment_shape(instance, assignment, "assignment")
    violations: list[Violation] = []
    usage = compute_usage(instance, assignment)

    # Ordinary capacity applies to every resource. For transient resources, the stronger
    # union-usage check below is reported instead to avoid duplicate diagnostics.
    for machine_id, machine in enumerate(instance.machines):
        for resource_id, resource in enumerate(instance.resources):
            if resource.transient:
                continue
            actual = usage[machine_id][resource_id]
            capacity = machine.capacities[resource_id]
            if actual > capacity:
                violations.append(
                    Violation(
                        constraint="capacity",
                        message=(
                            f"machine {machine_id} uses {actual} of resource {resource_id}, "
                            f"exceeding capacity {capacity}"
                        ),
                        machine=machine_id,
                        resource=resource_id,
                        actual=actual,
                        limit=capacity,
                    )
                )

    transient_usage = compute_transient_usage(instance, original, assignment)
    for machine_id, machine in enumerate(instance.machines):
        for resource_id, resource in enumerate(instance.resources):
            if not resource.transient:
                continue
            actual = transient_usage[machine_id][resource_id]
            capacity = machine.capacities[resource_id]
            if actual > capacity:
                violations.append(
                    Violation(
                        constraint="transient_capacity",
                        message=(
                            f"machine {machine_id} has transient usage {actual} of resource "
                            f"{resource_id}, exceeding capacity {capacity}"
                        ),
                        machine=machine_id,
                        resource=resource_id,
                        actual=actual,
                        limit=capacity,
                    )
                )

    service_machines: list[dict[int, list[int]]] = [
        {} for _ in range(instance.service_count)
    ]
    service_locations: list[set[int]] = [set() for _ in range(instance.service_count)]
    service_neighborhoods: list[set[int]] = [set() for _ in range(instance.service_count)]
    for process_id, machine_id in enumerate(assignment):
        service_id = instance.processes[process_id].service
        machine = instance.machines[machine_id]
        service_machines[service_id].setdefault(machine_id, []).append(process_id)
        service_locations[service_id].add(machine.location)
        service_neighborhoods[service_id].add(machine.neighborhood)

    for service_id, machine_processes in enumerate(service_machines):
        for machine_id, process_ids in machine_processes.items():
            if len(process_ids) > 1:
                violations.append(
                    Violation(
                        constraint="conflict",
                        message=(
                            f"service {service_id} has processes {process_ids} on machine "
                            f"{machine_id}"
                        ),
                        machine=machine_id,
                        service=service_id,
                        actual=len(process_ids),
                        limit=1,
                    )
                )

    for service_id, service in enumerate(instance.services):
        location_count = len(service_locations[service_id])
        if location_count < service.spread_min:
            violations.append(
                Violation(
                    constraint="spread",
                    message=(
                        f"service {service_id} covers {location_count} location(s); "
                        f"minimum is {service.spread_min}"
                    ),
                    service=service_id,
                    actual=location_count,
                    limit=service.spread_min,
                )
            )

        for dependency in service.dependencies:
            missing = service_neighborhoods[service_id] - service_neighborhoods[dependency]
            for neighborhood in sorted(missing):
                violations.append(
                    Violation(
                        constraint="dependency",
                        message=(
                            f"service {service_id} occurs in neighborhood {neighborhood} "
                            f"without required service {dependency}"
                        ),
                        service=service_id,
                        neighborhood=neighborhood,
                    )
                )

    return ValidationReport(feasible=not violations, violations=tuple(violations))

