"""Strict-feasible random-removal LNS with greedy and regret repair."""

from __future__ import annotations

import random
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import ObjectiveBreakdown, evaluate_objective
from gmrp_alns.gmrp.state import SolutionState
from gmrp_alns.gmrp.validator import validate
from gmrp_alns.search.common import build_result
from gmrp_alns.search.model import OperatorStats, SearchResult, TracePoint

RepairStrategy = Literal["greedy", "regret"]


@dataclass(frozen=True, slots=True)
class RepairOutcome:
    assignment: Assignment | None
    objective: ObjectiveBreakdown | None
    nodes: int
    candidate_evaluations: int


@dataclass(frozen=True, slots=True)
class _Option:
    machine: int
    delta: int


def _increment(row: dict[int, int], key: int, delta: int) -> None:
    updated = row.get(key, 0) + delta
    if updated < 0:  # pragma: no cover - internal invariant guard
        raise AssertionError("partial repair count became negative")
    if updated:
        row[key] = updated
    else:
        row.pop(key, None)


class _PartialRepairState:
    def __init__(
        self,
        instance: Instance,
        original: Assignment,
        incumbent: Assignment,
        removed: set[int],
    ) -> None:
        self.instance = instance
        self.original = original
        self.incumbent = incumbent
        self.assignment = list(incumbent)
        self.usage = [[0] * instance.resource_count for _ in range(instance.machine_count)]
        self.transient_usage = [
            [0] * instance.resource_count for _ in range(instance.machine_count)
        ]
        self.service_machine: list[dict[int, int]] = [
            {} for _ in range(instance.service_count)
        ]
        self.service_location: list[dict[int, int]] = [
            {} for _ in range(instance.service_count)
        ]
        self.service_neighborhood: list[dict[int, int]] = [
            {} for _ in range(instance.service_count)
        ]
        self.moved_by_service = [0] * instance.service_count

        for process, destination in enumerate(incumbent):
            definition = instance.processes[process]
            source = original[process]
            if process in removed:
                self.assignment[process] = -1
                for resource, resource_definition in enumerate(instance.resources):
                    if resource_definition.transient:
                        self.transient_usage[source][resource] += definition.requirements[
                            resource
                        ]
                continue

            for resource, requirement in enumerate(definition.requirements):
                self.usage[destination][resource] += requirement
                if instance.resources[resource].transient:
                    self.transient_usage[destination][resource] += requirement
                    if source != destination:
                        self.transient_usage[source][resource] += requirement
            service = definition.service
            machine = instance.machines[destination]
            _increment(self.service_machine[service], destination, 1)
            _increment(self.service_location[service], machine.location, 1)
            _increment(self.service_neighborhood[service], machine.neighborhood, 1)
            if source != destination:
                self.moved_by_service[service] += 1
        self.service_move_max = max(self.moved_by_service, default=0)

    def options(self, process: int) -> list[_Option]:
        definition = self.instance.processes[process]
        service = definition.service
        source = self.original[process]
        options: list[_Option] = []
        for destination, machine in enumerate(self.instance.machines):
            if self.service_machine[service].get(destination, 0):
                continue
            feasible = True
            for resource, requirement in enumerate(definition.requirements):
                if self.instance.resources[resource].transient:
                    added = requirement if destination != source else 0
                    if self.transient_usage[destination][resource] + added > machine.capacities[
                        resource
                    ]:
                        feasible = False
                        break
                elif self.usage[destination][resource] + requirement > machine.capacities[
                    resource
                ]:
                    feasible = False
                    break
            if feasible:
                options.append(_Option(destination, self.insertion_delta(process, destination)))
        options.sort(key=lambda option: (option.delta, option.machine))
        return options

    def insertion_delta(self, process: int, destination: int) -> int:
        definition = self.instance.processes[process]
        machine = self.instance.machines[destination]
        load_delta = 0
        for resource, requirement in enumerate(definition.requirements):
            before = self.usage[destination][resource]
            safety = machine.safety_capacities[resource]
            raw_delta = max(0, before + requirement - safety) - max(0, before - safety)
            load_delta += raw_delta * self.instance.resources[resource].load_cost_weight

        balance_delta = 0
        for balance in self.instance.balance_costs:
            available_first = machine.capacities[balance.first_resource] - self.usage[
                destination
            ][balance.first_resource]
            available_second = machine.capacities[balance.second_resource] - self.usage[
                destination
            ][balance.second_resource]
            new_first = available_first - definition.requirements[balance.first_resource]
            new_second = available_second - definition.requirements[balance.second_resource]
            raw_delta = max(0, balance.target * new_first - new_second) - max(
                0, balance.target * available_first - available_second
            )
            balance_delta += raw_delta * balance.weight

        source = self.original[process]
        process_delta = (
            definition.move_cost * self.instance.process_move_cost_weight
            if source != destination
            else 0
        )
        machine_delta = (
            self.instance.machines[source].move_costs[destination]
            * self.instance.machine_move_cost_weight
        )
        moved_count = self.moved_by_service[definition.service] + int(source != destination)
        service_delta = (
            max(self.service_move_max, moved_count) - self.service_move_max
        ) * self.instance.service_move_cost_weight
        return load_delta + balance_delta + process_delta + machine_delta + service_delta

    def apply(self, process: int, destination: int) -> None:
        definition = self.instance.processes[process]
        source = self.original[process]
        for resource, requirement in enumerate(definition.requirements):
            self.usage[destination][resource] += requirement
            if self.instance.resources[resource].transient and destination != source:
                self.transient_usage[destination][resource] += requirement
        service = definition.service
        machine = self.instance.machines[destination]
        _increment(self.service_machine[service], destination, 1)
        _increment(self.service_location[service], machine.location, 1)
        _increment(self.service_neighborhood[service], machine.neighborhood, 1)
        if source != destination:
            self.moved_by_service[service] += 1
            self.service_move_max = max(
                self.service_move_max, self.moved_by_service[service]
            )
        self.assignment[process] = destination

    def undo(self, process: int, destination: int) -> None:
        definition = self.instance.processes[process]
        source = self.original[process]
        for resource, requirement in enumerate(definition.requirements):
            self.usage[destination][resource] -= requirement
            if self.instance.resources[resource].transient and destination != source:
                self.transient_usage[destination][resource] -= requirement
        service = definition.service
        machine = self.instance.machines[destination]
        _increment(self.service_machine[service], destination, -1)
        _increment(self.service_location[service], machine.location, -1)
        _increment(self.service_neighborhood[service], machine.neighborhood, -1)
        if source != destination:
            self.moved_by_service[service] -= 1
            self.service_move_max = max(self.moved_by_service, default=0)
        self.assignment[process] = -1


def repair_removed(
    instance: Instance,
    original: Assignment,
    incumbent: Assignment,
    removed_processes: tuple[int, ...],
    *,
    strategy: RepairStrategy,
    deadline: float,
    top_k: int = 10,
    node_limit: int = 10_000,
) -> RepairOutcome:
    """Repair a random-removal neighborhood with bounded fail-first backtracking."""

    if strategy not in ("greedy", "regret"):
        raise ValueError(f"unknown repair strategy: {strategy}")
    if top_k <= 0 or node_limit <= 0:
        raise ValueError("top_k and node_limit must be positive")
    if len(set(removed_processes)) != len(removed_processes):
        raise ValueError("removed_processes contains duplicates")
    for process in removed_processes:
        if not 0 <= process < instance.process_count:
            raise ValueError(f"removed process {process} is out of range")
    if not removed_processes:
        objective = evaluate_objective(instance, original, incumbent)
        return RepairOutcome(incumbent, objective, 0, 0)

    partial = _PartialRepairState(instance, original, incumbent, set(removed_processes))
    remaining = set(removed_processes)
    nodes = 0
    evaluations = 0
    solution: Assignment | None = None
    solution_objective: ObjectiveBreakdown | None = None

    def search() -> bool:
        nonlocal nodes, evaluations, solution, solution_objective
        nodes += 1
        if nodes > node_limit or perf_counter() >= deadline:
            return False
        if not remaining:
            candidate = tuple(partial.assignment)
            report = validate(instance, original, candidate)
            if not report.feasible:
                return False
            solution = candidate
            solution_objective = evaluate_objective(instance, original, candidate)
            return True

        selected_process = -1
        selected_options: list[_Option] = []
        selected_key: tuple[float, ...] | None = None
        for process in sorted(remaining):
            options = partial.options(process)
            evaluations += instance.machine_count
            if not options:
                return False
            limited = options[:top_k]
            incumbent_machine = incumbent[process]
            incumbent_option = next(
                (option for option in options if option.machine == incumbent_machine),
                None,
            )
            if (
                incumbent_option is not None
                and all(option.machine != incumbent_machine for option in limited)
            ):
                limited.append(incumbent_option)
            if strategy == "regret":
                regret = (
                    float("inf")
                    if len(options) == 1
                    else float(options[1].delta - options[0].delta)
                )
                candidate_key: tuple[float, ...] = (
                    float(len(options) == 1),
                    regret,
                    -float(limited[0].delta),
                    -float(process),
                )
                better = selected_key is None or candidate_key > selected_key
            else:
                candidate_key = (float(limited[0].delta), float(process))
                better = selected_key is None or candidate_key < selected_key
            if better:
                selected_process = process
                selected_options = limited
                selected_key = candidate_key

        remaining.remove(selected_process)
        for option in selected_options:
            partial.apply(selected_process, option.machine)
            if search():
                return True
            partial.undo(selected_process, option.machine)
        remaining.add(selected_process)
        return False

    search()
    return RepairOutcome(solution, solution_objective, nodes, evaluations)


def random_lns(
    instance: Instance,
    original: Assignment,
    assignment: Assignment,
    *,
    repair: RepairStrategy = "greedy",
    time_limit_seconds: float = 60.0,
    seed: int = 0,
    max_iterations: int | None = None,
    destroy_size: int = 10,
    repair_top_k: int = 10,
    repair_node_limit: int = 10_000,
) -> SearchResult:
    """Run hill-climbing random removal with greedy or regret repair."""

    if repair not in ("greedy", "regret"):
        raise ValueError(f"unknown repair strategy: {repair}")
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    if max_iterations is not None and max_iterations < 0:
        raise ValueError("max_iterations must be non-negative")
    if destroy_size <= 0:
        raise ValueError("destroy_size must be positive")

    started = perf_counter()
    deadline = started + time_limit_seconds
    state = SolutionState(instance, original, assignment)
    initial_cost = evaluate_objective(instance, original, assignment).total_cost
    rng = random.Random(seed)
    trace = [TracePoint(0.0, 0, initial_cost, initial_cost, "initial")]
    time_to_best = 0.0
    iterations = 0
    evaluations = 0
    removal_calls = 0
    removal_successes = 0
    repair_calls = 0
    repair_successes = 0
    total_improvement = 0
    repair_seconds = 0.0
    process_ids = list(range(instance.process_count))

    while perf_counter() < deadline and (
        max_iterations is None or iterations < max_iterations
    ):
        iterations += 1
        removal_calls += 1
        removed = tuple(rng.sample(process_ids, min(destroy_size, len(process_ids))))
        repair_calls += 1
        repair_started = perf_counter()
        outcome = repair_removed(
            instance,
            original,
            state.assignment,
            removed,
            strategy=repair,
            deadline=deadline,
            top_k=repair_top_k,
            node_limit=repair_node_limit,
        )
        repair_seconds += perf_counter() - repair_started
        evaluations += outcome.candidate_evaluations
        if outcome.assignment is None or outcome.objective is None:
            continue
        repair_successes += 1
        if outcome.objective.total_cost >= state.total_cost:
            continue

        improvement = state.total_cost - outcome.objective.total_cost
        state = SolutionState(instance, original, outcome.assignment)
        removal_successes += 1
        total_improvement += improvement
        elapsed = perf_counter() - started
        time_to_best = elapsed
        trace.append(
            TracePoint(
                elapsed,
                iterations,
                state.total_cost,
                state.total_cost,
                f"random-removal-{repair}-repair",
            )
        )

    wall_time = perf_counter() - started
    operator_stats = {
        "random_removal": OperatorStats(
            calls=removal_calls,
            successes=removal_successes,
            candidate_evaluations=0,
            total_improvement=total_improvement,
            wall_time_seconds=0.0,
        ),
        f"{repair}_repair": OperatorStats(
            calls=repair_calls,
            successes=repair_successes,
            candidate_evaluations=evaluations,
            total_improvement=total_improvement,
            wall_time_seconds=repair_seconds,
        ),
    }
    return build_result(
        algorithm=f"random-lns-{repair}",
        state=state,
        initial=original,
        initial_cost=initial_cost,
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        wall_time_seconds=wall_time,
        time_to_best_seconds=time_to_best,
        iterations=iterations,
        candidate_evaluations=evaluations,
        trace=trace,
        operator_stats=operator_stats,
        config={
            "repair": repair,
            "destroy_size": destroy_size,
            "repair_top_k": repair_top_k,
            "repair_node_limit": repair_node_limit,
            "max_iterations": max_iterations,
        },
    )
