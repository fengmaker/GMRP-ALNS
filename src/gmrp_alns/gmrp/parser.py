"""Strict parser for the official whitespace-separated integer formats."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from gmrp_alns.gmrp.model import (
    Assignment,
    BalanceCost,
    Instance,
    Machine,
    Process,
    Resource,
    Service,
)


class ParseError(ValueError):
    """Raised when an instance or assignment violates its declared format."""


class _IntegerStream:
    def __init__(self, values: Iterable[int]) -> None:
        self._values = tuple(values)
        self._position = 0

    def take(self, label: str) -> int:
        if self._position >= len(self._values):
            raise ParseError(f"unexpected end of file while reading {label}")
        value = self._values[self._position]
        self._position += 1
        return value

    def take_nonnegative(self, label: str) -> int:
        value = self.take(label)
        if value < 0:
            raise ParseError(f"{label} must be non-negative, got {value}")
        return value

    def take_many(self, count: int, label: str) -> tuple[int, ...]:
        return tuple(self.take_nonnegative(f"{label}[{index}]") for index in range(count))

    def finish(self) -> None:
        remaining = len(self._values) - self._position
        if remaining:
            raise ParseError(f"unexpected {remaining} trailing integer(s)")


def _read_integers(path: str | Path) -> tuple[int, ...]:
    source = Path(path)
    try:
        tokens = source.read_text(encoding="utf-8-sig").split()
    except OSError as exc:
        raise ParseError(f"cannot read {source}: {exc}") from exc
    values: list[int] = []
    for index, token in enumerate(tokens):
        try:
            values.append(int(token))
        except ValueError as exc:
            raise ParseError(f"token {index + 1} is not an integer: {token!r}") from exc
    return tuple(values)


def _require_index(value: int, upper_bound: int, label: str) -> int:
    if not 0 <= value < upper_bound:
        raise ParseError(f"{label} index {value} is outside [0, {upper_bound})")
    return value


def parse_instance(path: str | Path) -> Instance:
    """Parse and structurally validate an official model file."""
    stream = _IntegerStream(_read_integers(path))

    resource_count = stream.take_nonnegative("resource count")
    if resource_count == 0:
        raise ParseError("resource count must be positive")
    resources: list[Resource] = []
    for resource_id in range(resource_count):
        transient_value = stream.take(f"resource[{resource_id}].transient")
        if transient_value not in (0, 1):
            raise ParseError(
                f"resource[{resource_id}].transient must be 0 or 1, got {transient_value}"
            )
        resources.append(
            Resource(
                transient=bool(transient_value),
                load_cost_weight=stream.take_nonnegative(
                    f"resource[{resource_id}].load_cost_weight"
                ),
            )
        )

    machine_count = stream.take_nonnegative("machine count")
    if machine_count == 0:
        raise ParseError("machine count must be positive")
    machines: list[Machine] = []
    for machine_id in range(machine_count):
        neighborhood = stream.take_nonnegative(f"machine[{machine_id}].neighborhood")
        location = stream.take_nonnegative(f"machine[{machine_id}].location")
        capacities = stream.take_many(resource_count, f"machine[{machine_id}].capacity")
        safety = stream.take_many(resource_count, f"machine[{machine_id}].safety_capacity")
        for resource_id, (safe, capacity) in enumerate(zip(safety, capacities, strict=True)):
            if safe > capacity:
                raise ParseError(
                    f"machine[{machine_id}].safety_capacity[{resource_id}] exceeds capacity"
                )
        machines.append(
            Machine(
                neighborhood=neighborhood,
                location=location,
                capacities=capacities,
                safety_capacities=safety,
                move_costs=stream.take_many(machine_count, f"machine[{machine_id}].move_cost"),
            )
        )

    service_count = stream.take_nonnegative("service count")
    if service_count == 0:
        raise ParseError("service count must be positive")
    services: list[Service] = []
    for service_id in range(service_count):
        spread_min = stream.take_nonnegative(f"service[{service_id}].spread_min")
        dependency_count = stream.take_nonnegative(f"service[{service_id}].dependency_count")
        dependencies = stream.take_many(dependency_count, f"service[{service_id}].dependency")
        for dependency in dependencies:
            _require_index(dependency, service_count, f"service[{service_id}].dependency")
        if len(set(dependencies)) != len(dependencies):
            raise ParseError(f"service[{service_id}] contains duplicate dependencies")
        services.append(Service(spread_min=spread_min, dependencies=dependencies))

    process_count = stream.take_nonnegative("process count")
    if process_count == 0:
        raise ParseError("process count must be positive")
    processes: list[Process] = []
    process_counts_by_service = [0] * service_count
    for process_id in range(process_count):
        process_service = _require_index(
            stream.take_nonnegative(f"process[{process_id}].service"),
            service_count,
            f"process[{process_id}].service",
        )
        process_counts_by_service[process_service] += 1
        processes.append(
            Process(
                service=process_service,
                requirements=stream.take_many(
                    resource_count, f"process[{process_id}].requirement"
                ),
                move_cost=stream.take_nonnegative(f"process[{process_id}].move_cost"),
            )
        )
    for service_id, service in enumerate(services):
        if service.spread_min > process_counts_by_service[service_id]:
            raise ParseError(
                f"service[{service_id}].spread_min exceeds its process count "
                f"({service.spread_min} > {process_counts_by_service[service_id]})"
            )

    balance_count = stream.take_nonnegative("balance cost count")
    balance_costs: list[BalanceCost] = []
    for balance_id in range(balance_count):
        first = _require_index(
            stream.take_nonnegative(f"balance[{balance_id}].first_resource"),
            resource_count,
            f"balance[{balance_id}].first_resource",
        )
        second = _require_index(
            stream.take_nonnegative(f"balance[{balance_id}].second_resource"),
            resource_count,
            f"balance[{balance_id}].second_resource",
        )
        balance_costs.append(
            BalanceCost(
                first_resource=first,
                second_resource=second,
                target=stream.take_nonnegative(f"balance[{balance_id}].target"),
                weight=stream.take_nonnegative(f"balance[{balance_id}].weight"),
            )
        )

    instance = Instance(
        resources=tuple(resources),
        machines=tuple(machines),
        services=tuple(services),
        processes=tuple(processes),
        balance_costs=tuple(balance_costs),
        process_move_cost_weight=stream.take_nonnegative("process move cost weight"),
        service_move_cost_weight=stream.take_nonnegative("service move cost weight"),
        machine_move_cost_weight=stream.take_nonnegative("machine move cost weight"),
    )
    stream.finish()
    return instance


def parse_assignment(path: str | Path, instance: Instance) -> Assignment:
    """Parse an official solution file and validate its cardinality and machine indices."""
    values = _read_integers(path)
    if len(values) != instance.process_count:
        raise ParseError(
            f"assignment contains {len(values)} values; expected {instance.process_count}"
        )
    return tuple(
        _require_index(machine, instance.machine_count, f"assignment[{process_id}]")
        for process_id, machine in enumerate(values)
    )


def write_assignment(path: str | Path, assignment: Assignment) -> None:
    """Write an assignment in the official one-line format."""
    destination = Path(path)
    destination.write_text(" ".join(map(str, assignment)) + "\n", encoding="utf-8")
