"""Immutable data objects for the official ROADEF 2012 problem format."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

Assignment: TypeAlias = tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Resource:
    transient: bool
    load_cost_weight: int


@dataclass(frozen=True, slots=True)
class Machine:
    neighborhood: int
    location: int
    capacities: tuple[int, ...]
    safety_capacities: tuple[int, ...]
    move_costs: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Service:
    spread_min: int
    dependencies: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Process:
    service: int
    requirements: tuple[int, ...]
    move_cost: int


@dataclass(frozen=True, slots=True)
class BalanceCost:
    first_resource: int
    second_resource: int
    target: int
    weight: int


@dataclass(frozen=True, slots=True)
class Instance:
    resources: tuple[Resource, ...]
    machines: tuple[Machine, ...]
    services: tuple[Service, ...]
    processes: tuple[Process, ...]
    balance_costs: tuple[BalanceCost, ...]
    process_move_cost_weight: int
    service_move_cost_weight: int
    machine_move_cost_weight: int

    @property
    def resource_count(self) -> int:
        return len(self.resources)

    @property
    def machine_count(self) -> int:
        return len(self.machines)

    @property
    def service_count(self) -> int:
        return len(self.services)

    @property
    def process_count(self) -> int:
        return len(self.processes)

    @property
    def neighborhood_count(self) -> int:
        return len({machine.neighborhood for machine in self.machines})

    @property
    def location_count(self) -> int:
        return len({machine.location for machine in self.machines})

    def summary(self) -> dict[str, int]:
        """Return stable, JSON-friendly instance dimensions."""
        return {
            "resources": self.resource_count,
            "machines": self.machine_count,
            "services": self.service_count,
            "processes": self.process_count,
            "neighborhoods": self.neighborhood_count,
            "locations": self.location_count,
            "balance_costs": len(self.balance_costs),
            "dependencies": sum(len(service.dependencies) for service in self.services),
            "transient_resources": sum(resource.transient for resource in self.resources),
        }

