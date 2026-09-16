"""Strict-feasible ALNS destroy selection heuristics."""

from __future__ import annotations

import random
from typing import Literal

from gmrp_alns.gmrp.state import SolutionState

DestroyStrategy = Literal[
    "random",
    "high-load",
    "resource-critical",
    "related-service",
    "high-move-gain",
]

DEFAULT_DESTROY_OPERATORS: tuple[DestroyStrategy, ...] = (
    "random",
    "high-load",
    "resource-critical",
    "related-service",
    "high-move-gain",
)


def _fill(
    selected: list[int],
    *,
    process_count: int,
    size: int,
    rng: random.Random,
) -> tuple[int, ...]:
    unique = list(dict.fromkeys(selected))
    chosen = set(unique)
    remaining = [process for process in range(process_count) if process not in chosen]
    rng.shuffle(remaining)
    unique.extend(remaining[: max(0, size - len(unique))])
    return tuple(unique[:size])


def _ranked_processes(
    scores: list[float], *, rng: random.Random
) -> list[int]:
    tie_breaks = [rng.random() for _ in scores]
    return sorted(
        range(len(scores)),
        key=lambda process: (-scores[process], tie_breaks[process]),
    )


def _load_relief(state: SolutionState, process: int) -> int:
    instance = state.instance
    destination = state.machine_of_process[process]
    definition = instance.processes[process]
    machine = instance.machines[destination]
    relief = 0
    for resource, requirement in enumerate(definition.requirements):
        before = state.usage[destination][resource]
        safety = machine.safety_capacities[resource]
        raw_relief = max(0, before - safety) - max(0, before - requirement - safety)
        relief += raw_relief * instance.resources[resource].load_cost_weight
    return relief


def select_destroy(
    state: SolutionState,
    strategy: DestroyStrategy,
    *,
    size: int,
    rng: random.Random,
) -> tuple[int, ...]:
    """Select unique process ids for one of five independently testable destroys."""

    if strategy not in DEFAULT_DESTROY_OPERATORS:
        raise ValueError(f"unknown destroy strategy: {strategy}")
    if size <= 0:
        raise ValueError("destroy size must be positive")
    count = state.instance.process_count
    actual_size = min(size, count)
    if strategy == "random":
        return tuple(rng.sample(range(count), actual_size))

    if strategy == "high-load":
        scores = [float(_load_relief(state, process)) for process in range(count)]
        return tuple(_ranked_processes(scores, rng=rng)[:actual_size])

    if strategy == "high-move-gain":
        scores = []
        instance = state.instance
        for process, destination in enumerate(state.machine_of_process):
            source = state.original[process]
            move_gain = _load_relief(state, process)
            if source != destination:
                move_gain += (
                    instance.processes[process].move_cost
                    * instance.process_move_cost_weight
                )
                move_gain += (
                    instance.machines[source].move_costs[destination]
                    * instance.machine_move_cost_weight
                )
            scores.append(float(move_gain))
        return tuple(_ranked_processes(scores, rng=rng)[:actual_size])

    if strategy == "resource-critical":
        instance = state.instance
        critical: list[tuple[float, int, int]] = []
        for machine_id, machine in enumerate(instance.machines):
            for resource in range(instance.resource_count):
                usage = (
                    state.transient_usage[machine_id][resource]
                    if instance.resources[resource].transient
                    else state.usage[machine_id][resource]
                )
                critical.append(
                    (usage / max(1, machine.capacities[resource]), machine_id, resource)
                )
        critical.sort(reverse=True)
        _, machine_id, resource = rng.choice(critical[: min(3, len(critical))])
        candidates = [
            process
            for process, destination in enumerate(state.machine_of_process)
            if destination == machine_id
        ]
        tie_breaks = {process: rng.random() for process in candidates}
        candidates.sort(
            key=lambda process: (
                -instance.processes[process].requirements[resource],
                tie_breaks[process],
            )
        )
        return _fill(candidates, process_count=count, size=actual_size, rng=rng)

    instance = state.instance
    seed_process = rng.randrange(count)
    seed_service = instance.processes[seed_process].service
    related_services = {seed_service, *instance.services[seed_service].dependencies}
    related_services.update(
        service
        for service, definition in enumerate(instance.services)
        if seed_service in definition.dependencies
    )
    candidates = [
        process
        for process, definition in enumerate(instance.processes)
        if definition.service in related_services
    ]
    rng.shuffle(candidates)
    return _fill(candidates, process_count=count, size=actual_size, rng=rng)
