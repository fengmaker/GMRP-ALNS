"""Cached feasible GMRP state with incremental relocate and swap evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TypeAlias

from gmrp_alns.gmrp.calculations import compute_transient_usage, compute_usage
from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import ObjectiveBreakdown, evaluate_objective
from gmrp_alns.gmrp.validator import validate


class InfeasibleMoveError(ValueError):
    """Raised when a move is stale, malformed, or violates a hard constraint."""


@dataclass(frozen=True, slots=True)
class RelocateMove:
    process: int
    source: int
    destination: int


@dataclass(frozen=True, slots=True)
class SwapMove:
    first_process: int
    second_process: int
    first_machine: int
    second_machine: int


Move: TypeAlias = RelocateMove | SwapMove


@dataclass(frozen=True, slots=True)
class ObjectiveDelta:
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
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MoveEvaluation:
    feasible: bool
    delta: ObjectiveDelta | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class SolutionSnapshot:
    assignment: Assignment
    usage: tuple[tuple[int, ...], ...]
    transient_usage: tuple[tuple[int, ...], ...]
    service_machine_count: tuple[tuple[tuple[int, int], ...], ...]
    service_location_count: tuple[tuple[tuple[int, int], ...], ...]
    service_neighborhood_count: tuple[tuple[tuple[int, int], ...], ...]
    moved_count_by_service: tuple[int, ...]
    moved_count_histogram: tuple[int, ...]
    objective: ObjectiveBreakdown


@dataclass(slots=True)
class _ChangePlan:
    destinations: dict[int, int]
    usage: dict[tuple[int, int], int]
    transient_usage: dict[tuple[int, int], int]
    service_machine: dict[tuple[int, int], int]
    service_location: dict[tuple[int, int], int]
    service_neighborhood: dict[tuple[int, int], int]
    moved_by_service: dict[int, int]


def _add_delta(target: dict[Any, int], key: Any, value: int) -> None:
    if value == 0:
        return
    updated = target.get(key, 0) + value
    if updated:
        target[key] = updated
    else:
        target.pop(key, None)


def _sparse_snapshot(rows: list[dict[int, int]]) -> tuple[tuple[tuple[int, int], ...], ...]:
    return tuple(tuple(sorted(row.items())) for row in rows)


class SolutionState:
    """A strictly feasible assignment plus all caches touched by M3 moves."""

    def __init__(self, instance: Instance, original: Assignment, assignment: Assignment) -> None:
        report = validate(instance, original, assignment)
        if not report.feasible:
            first = report.violations[0].message if report.violations else "unknown violation"
            raise ValueError(f"SolutionState requires a feasible assignment: {first}")
        self.instance = instance
        self.original = original
        self.machine_of_process = list(assignment)
        self.usage = compute_usage(instance, assignment)
        self.transient_usage = compute_transient_usage(instance, original, assignment)

        locations = sorted({machine.location for machine in instance.machines})
        neighborhoods = sorted({machine.neighborhood for machine in instance.machines})
        location_index = {location: index for index, location in enumerate(locations)}
        neighborhood_index = {
            neighborhood: index for index, neighborhood in enumerate(neighborhoods)
        }
        self.machine_location = [location_index[machine.location] for machine in instance.machines]
        self.machine_neighborhood = [
            neighborhood_index[machine.neighborhood] for machine in instance.machines
        ]

        self.service_machine_count: list[dict[int, int]] = [
            {} for _ in range(instance.service_count)
        ]
        self.service_location_count: list[dict[int, int]] = [
            {} for _ in range(instance.service_count)
        ]
        self.service_neighborhood_count: list[dict[int, int]] = [
            {} for _ in range(instance.service_count)
        ]
        self.moved_count_by_service = [0] * instance.service_count
        for process_id, machine_id in enumerate(assignment):
            service = instance.processes[process_id].service
            self._increment_sparse(self.service_machine_count[service], machine_id, 1)
            self._increment_sparse(
                self.service_location_count[service], self.machine_location[machine_id], 1
            )
            self._increment_sparse(
                self.service_neighborhood_count[service],
                self.machine_neighborhood[machine_id],
                1,
            )
            if machine_id != original[process_id]:
                self.moved_count_by_service[service] += 1

        self.moved_count_histogram = [0] * (instance.process_count + 1)
        for count in self.moved_count_by_service:
            self.moved_count_histogram[count] += 1
        self.reverse_dependencies: list[set[int]] = [
            set() for _ in range(instance.service_count)
        ]
        for service, definition in enumerate(instance.services):
            for dependency in definition.dependencies:
                self.reverse_dependencies[dependency].add(service)
        self.objective = evaluate_objective(instance, original, assignment)

    @staticmethod
    def _increment_sparse(row: dict[int, int], key: int, delta: int) -> None:
        updated = row.get(key, 0) + delta
        if updated < 0:
            raise AssertionError(f"negative sparse count for key {key}")
        if updated:
            row[key] = updated
        else:
            row.pop(key, None)

    @property
    def assignment(self) -> Assignment:
        return tuple(self.machine_of_process)

    @property
    def total_cost(self) -> int:
        return self.objective.total_cost

    def make_relocate(self, process: int, destination: int) -> RelocateMove:
        self._require_process(process)
        self._require_machine(destination)
        return RelocateMove(process, self.machine_of_process[process], destination)

    def make_swap(self, first_process: int, second_process: int) -> SwapMove:
        self._require_process(first_process)
        self._require_process(second_process)
        return SwapMove(
            first_process,
            second_process,
            self.machine_of_process[first_process],
            self.machine_of_process[second_process],
        )

    def _require_process(self, process: int) -> None:
        if not 0 <= process < self.instance.process_count:
            raise IndexError(f"process {process} is outside [0, {self.instance.process_count})")

    def _require_machine(self, machine: int) -> None:
        if not 0 <= machine < self.instance.machine_count:
            raise IndexError(f"machine {machine} is outside [0, {self.instance.machine_count})")

    def evaluate_move(self, move: Move) -> MoveEvaluation:
        evaluation, _ = self._evaluate_move(move)
        return evaluation

    def _evaluate_move(self, move: Move) -> tuple[MoveEvaluation, _ChangePlan | None]:
        try:
            destinations = self._destinations_for_apply(move)
        except InfeasibleMoveError as exc:
            return MoveEvaluation(False, None, str(exc)), None
        plan = self._build_plan(destinations)
        reason = self._constraint_failure(plan)
        if reason is not None:
            return MoveEvaluation(False, None, reason), plan
        return MoveEvaluation(True, self._objective_delta(plan), None), plan

    def is_move_feasible(self, move: Move) -> bool:
        return self.evaluate_move(move).feasible

    def can_relocate(self, process: int, destination: int) -> bool:
        return self.is_move_feasible(self.make_relocate(process, destination))

    def relocate_delta(self, process: int, destination: int) -> ObjectiveDelta:
        evaluation = self.evaluate_move(self.make_relocate(process, destination))
        if not evaluation.feasible or evaluation.delta is None:
            raise InfeasibleMoveError(evaluation.reason or "relocate is infeasible")
        return evaluation.delta

    def apply_relocate(self, process: int, destination: int) -> RelocateMove:
        move = self.make_relocate(process, destination)
        self.apply_move(move)
        return move

    def undo_relocate(self, move: RelocateMove) -> ObjectiveDelta:
        return self.undo_move(move)

    def can_swap(self, first_process: int, second_process: int) -> bool:
        return self.is_move_feasible(self.make_swap(first_process, second_process))

    def swap_delta(self, first_process: int, second_process: int) -> ObjectiveDelta:
        evaluation = self.evaluate_move(self.make_swap(first_process, second_process))
        if not evaluation.feasible or evaluation.delta is None:
            raise InfeasibleMoveError(evaluation.reason or "swap is infeasible")
        return evaluation.delta

    def apply_swap(self, first_process: int, second_process: int) -> SwapMove:
        move = self.make_swap(first_process, second_process)
        self.apply_move(move)
        return move

    def undo_swap(self, move: SwapMove) -> ObjectiveDelta:
        return self.undo_move(move)

    def apply_move(self, move: Move) -> ObjectiveDelta:
        evaluation, plan = self._evaluate_move(move)
        if not evaluation.feasible or evaluation.delta is None or plan is None:
            raise InfeasibleMoveError(evaluation.reason or "move is infeasible")
        self._apply_plan(plan, evaluation.delta)
        return evaluation.delta

    def undo_move(self, move: Move) -> ObjectiveDelta:
        destinations = self._destinations_for_undo(move)
        plan = self._build_plan(destinations)
        reason = self._constraint_failure(plan)
        if reason is not None:  # pragma: no cover - a valid inverse must remain feasible
            raise AssertionError(f"inverse move became infeasible: {reason}")
        delta = self._objective_delta(plan)
        self._apply_plan(plan, delta)
        return delta

    def _destinations_for_apply(self, move: Move) -> dict[int, int]:
        if isinstance(move, RelocateMove):
            self._require_process(move.process)
            self._require_machine(move.destination)
            if self.machine_of_process[move.process] != move.source:
                raise InfeasibleMoveError("relocate move is stale")
            if move.source == move.destination:
                raise InfeasibleMoveError("relocate source and destination are identical")
            return {move.process: move.destination}

        self._require_process(move.first_process)
        self._require_process(move.second_process)
        if move.first_process == move.second_process:
            raise InfeasibleMoveError("swap processes are identical")
        if (
            self.machine_of_process[move.first_process] != move.first_machine
            or self.machine_of_process[move.second_process] != move.second_machine
        ):
            raise InfeasibleMoveError("swap move is stale")
        if move.first_machine == move.second_machine:
            raise InfeasibleMoveError("swap processes already share a machine")
        return {
            move.first_process: move.second_machine,
            move.second_process: move.first_machine,
        }

    def _destinations_for_undo(self, move: Move) -> dict[int, int]:
        if isinstance(move, RelocateMove):
            if self.machine_of_process[move.process] != move.destination:
                raise InfeasibleMoveError("relocate move cannot be undone from this state")
            return {move.process: move.source}
        if (
            self.machine_of_process[move.first_process] != move.second_machine
            or self.machine_of_process[move.second_process] != move.first_machine
        ):
            raise InfeasibleMoveError("swap move cannot be undone from this state")
        return {
            move.first_process: move.first_machine,
            move.second_process: move.second_machine,
        }

    def _build_plan(self, destinations: dict[int, int]) -> _ChangePlan:
        plan = _ChangePlan({}, {}, {}, {}, {}, {}, {})
        for process_id, destination in destinations.items():
            source = self.machine_of_process[process_id]
            if source == destination:
                continue
            plan.destinations[process_id] = destination
            process = self.instance.processes[process_id]
            service = process.service
            for resource, requirement in enumerate(process.requirements):
                _add_delta(plan.usage, (source, resource), -requirement)
                _add_delta(plan.usage, (destination, resource), requirement)
                if self.instance.resources[resource].transient:
                    old_endpoints = {self.original[process_id], source}
                    new_endpoints = {self.original[process_id], destination}
                    for machine in old_endpoints - new_endpoints:
                        _add_delta(plan.transient_usage, (machine, resource), -requirement)
                    for machine in new_endpoints - old_endpoints:
                        _add_delta(plan.transient_usage, (machine, resource), requirement)

            _add_delta(plan.service_machine, (service, source), -1)
            _add_delta(plan.service_machine, (service, destination), 1)
            _add_delta(
                plan.service_location,
                (service, self.machine_location[source]),
                -1,
            )
            _add_delta(
                plan.service_location,
                (service, self.machine_location[destination]),
                1,
            )
            _add_delta(
                plan.service_neighborhood,
                (service, self.machine_neighborhood[source]),
                -1,
            )
            _add_delta(
                plan.service_neighborhood,
                (service, self.machine_neighborhood[destination]),
                1,
            )
            old_moved = int(source != self.original[process_id])
            new_moved = int(destination != self.original[process_id])
            _add_delta(plan.moved_by_service, service, new_moved - old_moved)
        return plan

    def _constraint_failure(self, plan: _ChangePlan) -> str | None:
        for (machine, resource), delta in plan.usage.items():
            if self.instance.resources[resource].transient:
                continue
            actual = self.usage[machine][resource] + delta
            if actual > self.instance.machines[machine].capacities[resource]:
                return f"capacity violation on machine {machine}, resource {resource}"
        for (machine, resource), delta in plan.transient_usage.items():
            actual = self.transient_usage[machine][resource] + delta
            if actual > self.instance.machines[machine].capacities[resource]:
                return f"transient capacity violation on machine {machine}, resource {resource}"
        for (service, machine), delta in plan.service_machine.items():
            actual = self.service_machine_count[service].get(machine, 0) + delta
            if not 0 <= actual <= 1:
                return f"service {service} conflict on machine {machine}"

        changed_services = (
            {service for service, _ in plan.service_machine}
            | {service for service, _ in plan.service_location}
            | {service for service, _ in plan.service_neighborhood}
            | set(plan.moved_by_service)
        )
        for service in changed_services:
            location_count = len(self.service_location_count[service])
            for (changed_service, location), delta in plan.service_location.items():
                if changed_service != service:
                    continue
                before = self.service_location_count[service].get(location, 0)
                after = before + delta
                if after < 0:
                    return f"negative location count for service {service}"
                if before == 0 and after > 0:
                    location_count += 1
                elif before > 0 and after == 0:
                    location_count -= 1
            if location_count < self.instance.services[service].spread_min:
                return f"spread violation for service {service}"

        dependency_services = set(changed_services)
        for service in changed_services:
            dependency_services.update(self.reverse_dependencies[service])
        for service in dependency_services:
            definition = self.instance.services[service]
            relevant_neighborhoods = set(self.service_neighborhood_count[service])
            relevant_neighborhoods.update(
                neighborhood
                for changed_service, neighborhood in plan.service_neighborhood
                if changed_service == service
            )
            for neighborhood in relevant_neighborhoods:
                if self._neighborhood_count_after(service, neighborhood, plan) <= 0:
                    continue
                for dependency in definition.dependencies:
                    if self._neighborhood_count_after(dependency, neighborhood, plan) <= 0:
                        return (
                            f"dependency violation: service {service} requires {dependency} "
                            f"in neighborhood {neighborhood}"
                        )
        return None

    def _neighborhood_count_after(
        self, service: int, neighborhood: int, plan: _ChangePlan
    ) -> int:
        return self.service_neighborhood_count[service].get(neighborhood, 0) + (
            plan.service_neighborhood.get((service, neighborhood), 0)
        )

    def _objective_delta(self, plan: _ChangePlan) -> ObjectiveDelta:
        load_deltas = [0] * self.instance.resource_count
        for (machine, resource), delta in plan.usage.items():
            old_usage = self.usage[machine][resource]
            safety = self.instance.machines[machine].safety_capacities[resource]
            load_deltas[resource] += max(0, old_usage + delta - safety) - max(
                0, old_usage - safety
            )

        affected_machines = {machine for machine, _ in plan.usage}
        balance_deltas: list[int] = []
        for balance in self.instance.balance_costs:
            difference = 0
            for machine_id in affected_machines:
                machine_definition = self.instance.machines[machine_id]
                old_first = machine_definition.capacities[
                    balance.first_resource
                ] - self.usage[machine_id][balance.first_resource]
                old_second = machine_definition.capacities[
                    balance.second_resource
                ] - self.usage[machine_id][balance.second_resource]
                new_first = old_first - plan.usage.get(
                    (machine_id, balance.first_resource), 0
                )
                new_second = old_second - plan.usage.get(
                    (machine_id, balance.second_resource), 0
                )
                difference += max(0, balance.target * new_first - new_second) - max(
                    0, balance.target * old_first - old_second
                )
            balance_deltas.append(difference)

        process_move_delta = 0
        machine_move_delta = 0
        for process_id, destination in plan.destinations.items():
            current = self.machine_of_process[process_id]
            source = self.original[process_id]
            process = self.instance.processes[process_id]
            process_move_delta += process.move_cost * (
                int(destination != source) - int(current != source)
            )
            machine_move_delta += (
                self.instance.machines[source].move_costs[destination]
                - self.instance.machines[source].move_costs[current]
            )

        new_service_max = self._service_move_max_after(plan.moved_by_service)
        service_move_delta = new_service_max - self.objective.service_move_cost
        weighted_load = sum(
            delta * resource.load_cost_weight
            for delta, resource in zip(load_deltas, self.instance.resources, strict=True)
        )
        weighted_balance = sum(
            delta * balance.weight
            for delta, balance in zip(
                balance_deltas, self.instance.balance_costs, strict=True
            )
        )
        weighted_process = process_move_delta * self.instance.process_move_cost_weight
        weighted_service = service_move_delta * self.instance.service_move_cost_weight
        weighted_machine = machine_move_delta * self.instance.machine_move_cost_weight
        return ObjectiveDelta(
            load_costs=tuple(load_deltas),
            balance_costs=tuple(balance_deltas),
            process_move_cost=process_move_delta,
            service_move_cost=service_move_delta,
            machine_move_cost=machine_move_delta,
            weighted_load_cost=weighted_load,
            weighted_balance_cost=weighted_balance,
            weighted_process_move_cost=weighted_process,
            weighted_service_move_cost=weighted_service,
            weighted_machine_move_cost=weighted_machine,
            total_cost=(
                weighted_load
                + weighted_balance
                + weighted_process
                + weighted_service
                + weighted_machine
            ),
        )

    def _service_move_max_after(self, deltas: dict[int, int]) -> int:
        histogram_delta: dict[int, int] = {}
        for service, delta in deltas.items():
            old = self.moved_count_by_service[service]
            new = old + delta
            _add_delta(histogram_delta, old, -1)
            _add_delta(histogram_delta, new, 1)
        candidate = max(
            [self.objective.service_move_cost]
            + [self.moved_count_by_service[service] + delta for service, delta in deltas.items()]
        )
        while candidate > 0:
            if self.moved_count_histogram[candidate] + histogram_delta.get(candidate, 0) > 0:
                return candidate
            candidate -= 1
        return 0

    def _apply_plan(self, plan: _ChangePlan, delta: ObjectiveDelta) -> None:
        for (machine, resource), change in plan.usage.items():
            self.usage[machine][resource] += change
        for (machine, resource), change in plan.transient_usage.items():
            self.transient_usage[machine][resource] += change
        for (service, machine), change in plan.service_machine.items():
            self._increment_sparse(self.service_machine_count[service], machine, change)
        for (service, location), change in plan.service_location.items():
            self._increment_sparse(self.service_location_count[service], location, change)
        for (service, neighborhood), change in plan.service_neighborhood.items():
            self._increment_sparse(
                self.service_neighborhood_count[service], neighborhood, change
            )
        for service, change in plan.moved_by_service.items():
            old_count = self.moved_count_by_service[service]
            new = old_count + change
            self.moved_count_histogram[old_count] -= 1
            self.moved_count_histogram[new] += 1
            self.moved_count_by_service[service] = new
        for process, destination in plan.destinations.items():
            self.machine_of_process[process] = destination

        current_objective = self.objective
        self.objective = ObjectiveBreakdown(
            load_costs=tuple(
                value + change
                for value, change in zip(
                    current_objective.load_costs, delta.load_costs, strict=True
                )
            ),
            balance_costs=tuple(
                value + change
                for value, change in zip(
                    current_objective.balance_costs, delta.balance_costs, strict=True
                )
            ),
            process_move_cost=(
                current_objective.process_move_cost + delta.process_move_cost
            ),
            service_move_cost=(
                current_objective.service_move_cost + delta.service_move_cost
            ),
            machine_move_cost=(
                current_objective.machine_move_cost + delta.machine_move_cost
            ),
            weighted_load_cost=(
                current_objective.weighted_load_cost + delta.weighted_load_cost
            ),
            weighted_balance_cost=(
                current_objective.weighted_balance_cost + delta.weighted_balance_cost
            ),
            weighted_process_move_cost=(
                current_objective.weighted_process_move_cost
                + delta.weighted_process_move_cost
            ),
            weighted_service_move_cost=(
                current_objective.weighted_service_move_cost
                + delta.weighted_service_move_cost
            ),
            weighted_machine_move_cost=(
                current_objective.weighted_machine_move_cost
                + delta.weighted_machine_move_cost
            ),
            total_cost=current_objective.total_cost + delta.total_cost,
        )

    def prefilter_machines(self, process: int) -> tuple[int, ...]:
        """Return cheap capacity/conflict-feasible relocate destinations."""

        self._require_process(process)
        source = self.machine_of_process[process]
        definition = self.instance.processes[process]
        candidates: list[int] = []
        for destination in range(self.instance.machine_count):
            if destination == source:
                continue
            if self.service_machine_count[definition.service].get(destination, 0):
                continue
            plan = self._build_plan({process: destination})
            capacity_failure = False
            for (machine, resource), delta in plan.usage.items():
                if self.instance.resources[resource].transient:
                    continue
                if (
                    self.usage[machine][resource] + delta
                    > self.instance.machines[machine].capacities[resource]
                ):
                    capacity_failure = True
                    break
            if capacity_failure:
                continue
            for (machine, resource), delta in plan.transient_usage.items():
                if (
                    self.transient_usage[machine][resource] + delta
                    > self.instance.machines[machine].capacities[resource]
                ):
                    capacity_failure = True
                    break
            if not capacity_failure:
                candidates.append(destination)
        return tuple(candidates)

    def candidate_machines(self, process: int, *, top_k: int = 20) -> tuple[int, ...]:
        """Return the best fully feasible Top-K relocate destinations by exact delta."""

        if top_k <= 0:
            raise ValueError("top_k must be positive")
        ranked: list[tuple[int, int]] = []
        for destination in self.prefilter_machines(process):
            move = self.make_relocate(process, destination)
            evaluation = self.evaluate_move(move)
            if evaluation.feasible and evaluation.delta is not None:
                ranked.append((evaluation.delta.total_cost, destination))
        ranked.sort()
        return tuple(destination for _, destination in ranked[:top_k])

    def snapshot(self) -> SolutionSnapshot:
        return SolutionSnapshot(
            assignment=self.assignment,
            usage=tuple(tuple(row) for row in self.usage),
            transient_usage=tuple(tuple(row) for row in self.transient_usage),
            service_machine_count=_sparse_snapshot(self.service_machine_count),
            service_location_count=_sparse_snapshot(self.service_location_count),
            service_neighborhood_count=_sparse_snapshot(self.service_neighborhood_count),
            moved_count_by_service=tuple(self.moved_count_by_service),
            moved_count_histogram=tuple(self.moved_count_histogram),
            objective=self.objective,
        )

    def assert_consistent(self) -> None:
        """Compare every cache with a fresh full reconstruction oracle."""

        rebuilt = SolutionState(self.instance, self.original, self.assignment)
        if self.snapshot() != rebuilt.snapshot():
            raise AssertionError("incremental state differs from full reconstruction")
