"""Bounded CP-SAT repair for a restricted GMRP neighborhood."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from time import perf_counter

from ortools.sat.python import cp_model

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import ObjectiveBreakdown, evaluate_objective
from gmrp_alns.gmrp.validator import validate


@dataclass(frozen=True, slots=True)
class RestrictedRepairCall:
    """One exact-repair attempt and the telemetry needed by M6 experiments."""

    assignment: Assignment | None
    objective: ObjectiveBreakdown | None
    status: str
    wall_time_seconds: float
    solver_time_limit_seconds: float
    assignment_variables: int
    branches: int
    conflicts: int
    best_bound: int | None

    @property
    def improved(self) -> bool:
        return self.assignment is not None and self.objective is not None


@dataclass(frozen=True, slots=True)
class _Candidate:
    machine: int
    score: int


def _empty_call(
    status: str,
    *,
    started: float,
    solver_time_limit_seconds: float = 0.0,
    assignment_variables: int = 0,
) -> RestrictedRepairCall:
    return RestrictedRepairCall(
        assignment=None,
        objective=None,
        status=status,
        wall_time_seconds=perf_counter() - started,
        solver_time_limit_seconds=solver_time_limit_seconds,
        assignment_variables=assignment_variables,
        branches=0,
        conflicts=0,
        best_bound=None,
    )


def _fixed_data(
    instance: Instance,
    original: Assignment,
    incumbent: Assignment,
    removed: set[int],
    *,
    deadline: float,
) -> tuple[
    list[list[int]],
    list[list[int]],
    list[set[int]],
    list[set[int]],
    list[set[int]],
    list[int],
    int,
    int,
] | None:
    fixed_usage = [[0] * instance.resource_count for _ in range(instance.machine_count)]
    fixed_transient = [
        [0] * instance.resource_count for _ in range(instance.machine_count)
    ]
    fixed_machines: list[set[int]] = [set() for _ in range(instance.service_count)]
    fixed_locations: list[set[int]] = [set() for _ in range(instance.service_count)]
    fixed_neighborhoods: list[set[int]] = [
        set() for _ in range(instance.service_count)
    ]
    fixed_moved_by_service = [0] * instance.service_count
    fixed_process_move = 0
    fixed_machine_move = 0

    for process_id, destination in enumerate(incumbent):
        if process_id % 256 == 0 and perf_counter() >= deadline:
            return None
        process = instance.processes[process_id]
        source = original[process_id]
        if process_id in removed:
            for resource, resource_definition in enumerate(instance.resources):
                if resource_definition.transient:
                    fixed_transient[source][resource] += process.requirements[resource]
            continue
        for resource, requirement in enumerate(process.requirements):
            fixed_usage[destination][resource] += requirement
            if instance.resources[resource].transient:
                fixed_transient[destination][resource] += requirement
                if source != destination:
                    fixed_transient[source][resource] += requirement
        service = process.service
        machine = instance.machines[destination]
        fixed_machines[service].add(destination)
        fixed_locations[service].add(machine.location)
        fixed_neighborhoods[service].add(machine.neighborhood)
        if source != destination:
            fixed_moved_by_service[service] += 1
            fixed_process_move += process.move_cost
        fixed_machine_move += instance.machines[source].move_costs[destination]

    return (
        fixed_usage,
        fixed_transient,
        fixed_machines,
        fixed_locations,
        fixed_neighborhoods,
        fixed_moved_by_service,
        fixed_process_move,
        fixed_machine_move,
    )


def _candidate_score(
    instance: Instance,
    original: Assignment,
    fixed_usage: list[list[int]],
    process_id: int,
    destination: int,
) -> int:
    process = instance.processes[process_id]
    machine = instance.machines[destination]
    score = instance.machines[original[process_id]].move_costs[destination]
    score *= instance.machine_move_cost_weight
    if destination != original[process_id]:
        score += process.move_cost * instance.process_move_cost_weight
    for resource, requirement in enumerate(process.requirements):
        before = fixed_usage[destination][resource]
        safety = machine.safety_capacities[resource]
        score += (
            max(0, before + requirement - safety) - max(0, before - safety)
        ) * instance.resources[resource].load_cost_weight
    for balance in instance.balance_costs:
        before_first = (
            machine.capacities[balance.first_resource]
            - fixed_usage[destination][balance.first_resource]
        )
        before_second = (
            machine.capacities[balance.second_resource]
            - fixed_usage[destination][balance.second_resource]
        )
        after_first = before_first - process.requirements[balance.first_resource]
        after_second = before_second - process.requirements[balance.second_resource]
        score += (
            max(0, balance.target * after_first - after_second)
            - max(0, balance.target * before_first - before_second)
        ) * balance.weight
    return score


def _candidate_machines(
    instance: Instance,
    original: Assignment,
    incumbent: Assignment,
    processes: tuple[int, ...],
    *,
    fixed_usage: list[list[int]],
    fixed_transient: list[list[int]],
    fixed_machines: list[set[int]],
    candidate_limit: int,
    variable_limit: int,
    deadline: float,
) -> dict[int, tuple[int, ...]] | None:
    if variable_limit < len(processes):
        return None
    ranked: dict[int, list[_Candidate]] = {}
    for process_id in processes:
        process = instance.processes[process_id]
        source = original[process_id]
        candidates: list[_Candidate] = []
        for destination, machine in enumerate(instance.machines):
            if perf_counter() >= deadline:
                return None
            if destination in fixed_machines[process.service]:
                continue
            feasible = True
            for resource, requirement in enumerate(process.requirements):
                if instance.resources[resource].transient:
                    added = requirement if destination != source else 0
                    usage = fixed_transient[destination][resource] + added
                else:
                    usage = fixed_usage[destination][resource] + requirement
                if usage > machine.capacities[resource]:
                    feasible = False
                    break
            if feasible:
                candidates.append(
                    _Candidate(
                        destination,
                        _candidate_score(
                            instance,
                            original,
                            fixed_usage,
                            process_id,
                            destination,
                        ),
                    )
                )
        candidates.sort(key=lambda candidate: (candidate.score, candidate.machine))
        current = incumbent[process_id]
        current_candidate = next(
            (candidate for candidate in candidates if candidate.machine == current),
            None,
        )
        if current_candidate is None:  # pragma: no cover - feasible incumbent invariant
            raise AssertionError("incumbent machine was removed from its restricted domain")
        process_alternatives = [
            candidate for candidate in candidates if candidate.machine != current
        ]
        ranked[process_id] = [
            current_candidate,
            *process_alternatives[: candidate_limit - 1],
        ]

    selected = {process_id: [incumbent[process_id]] for process_id in processes}
    remaining_slots = variable_limit - len(processes)
    alternative_rows = sorted(
        (
            candidate.score,
            rank,
            process_id,
            candidate.machine,
        )
        for process_id, candidates in ranked.items()
        for rank, candidate in enumerate(candidates[1:], start=1)
    )
    for _, _, process_id, destination in alternative_rows[:remaining_slots]:
        selected[process_id].append(destination)
    return {process_id: tuple(machines) for process_id, machines in selected.items()}


def restricted_cpsat_repair(
    instance: Instance,
    original: Assignment,
    incumbent: Assignment,
    removed_processes: tuple[int, ...],
    *,
    deadline: float,
    time_limit_seconds: float = 0.1,
    candidate_machine_limit: int = 10,
    variable_limit: int = 200,
    seed: int = 0,
) -> RestrictedRepairCall:
    """Optimize a fixed-complement neighborhood and return only a verified improvement."""

    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    if candidate_machine_limit <= 0 or variable_limit <= 0:
        raise ValueError("candidate_machine_limit and variable_limit must be positive")
    if len(set(removed_processes)) != len(removed_processes):
        raise ValueError("removed_processes contains duplicates")
    for process_id in removed_processes:
        if not 0 <= process_id < instance.process_count:
            raise ValueError(f"removed process {process_id} is out of range")

    started = perf_counter()
    call_deadline = min(deadline, started + time_limit_seconds)
    if not removed_processes:
        return _empty_call("empty_neighborhood", started=started)
    if call_deadline <= started:
        return _empty_call("deadline_before_build", started=started)

    processes = tuple(sorted(removed_processes))
    removed = set(processes)
    fixed = _fixed_data(
        instance,
        original,
        incumbent,
        removed,
        deadline=call_deadline,
    )
    if fixed is None:
        return _empty_call("deadline_during_fixed_data", started=started)
    (
        fixed_usage,
        fixed_transient,
        fixed_machines,
        fixed_locations,
        fixed_neighborhoods,
        fixed_moved_by_service,
        fixed_process_move,
        fixed_machine_move,
    ) = fixed
    domains = _candidate_machines(
        instance,
        original,
        incumbent,
        processes,
        fixed_usage=fixed_usage,
        fixed_transient=fixed_transient,
        fixed_machines=fixed_machines,
        candidate_limit=candidate_machine_limit,
        variable_limit=variable_limit,
        deadline=call_deadline,
    )
    if domains is None:
        status = (
            "variable_limit"
            if variable_limit < len(processes)
            else "deadline_during_candidates"
        )
        return _empty_call(status, started=started)
    if perf_counter() >= call_deadline:
        return _empty_call("deadline_before_model", started=started)

    model = cp_model.CpModel()
    variables = {
        (process_id, machine): model.new_bool_var(f"x_{process_id}_{machine}")
        for process_id in processes
        for machine in domains[process_id]
    }
    assignment_variable_count = len(variables)
    for process_id in processes:
        row = [variables[process_id, machine] for machine in domains[process_id]]
        model.add_exactly_one(row)
        for machine in domains[process_id]:
            model.add_hint(
                variables[process_id, machine],
                int(machine == incumbent[process_id]),
            )

    by_machine: dict[int, list[tuple[int, cp_model.IntVar]]] = defaultdict(list)
    by_service_machine: dict[tuple[int, int], list[cp_model.IntVar]] = defaultdict(list)
    by_service_location: dict[tuple[int, int], list[cp_model.IntVar]] = defaultdict(list)
    by_service_neighborhood: dict[
        tuple[int, int], list[cp_model.IntVar]
    ] = defaultdict(list)
    for (process_id, machine), variable in variables.items():
        service = instance.processes[process_id].service
        definition = instance.machines[machine]
        by_machine[machine].append((process_id, variable))
        by_service_machine[service, machine].append(variable)
        by_service_location[service, definition.location].append(variable)
        by_service_neighborhood[service, definition.neighborhood].append(variable)

    affected_machines = set(by_machine)
    affected_services = {
        instance.processes[process_id].service for process_id in processes
    }
    usage_expressions: dict[tuple[int, int], cp_model.LinearExpr | int] = {}
    for machine in affected_machines:
        if perf_counter() >= call_deadline:
            return _empty_call(
                "deadline_during_model",
                started=started,
                assignment_variables=assignment_variable_count,
            )
        machine_terms = by_machine[machine]
        for resource in range(instance.resource_count):
            usage = fixed_usage[machine][resource] + sum(
                instance.processes[process_id].requirements[resource] * variable
                for process_id, variable in machine_terms
            )
            usage_expressions[machine, resource] = usage
            model.add(usage <= instance.machines[machine].capacities[resource])
            if instance.resources[resource].transient:
                transient = fixed_transient[machine][resource] + sum(
                    instance.processes[process_id].requirements[resource] * variable
                    for process_id, variable in machine_terms
                    if original[process_id] != machine
                )
                model.add(transient <= instance.machines[machine].capacities[resource])

    for (service, machine), row in by_service_machine.items():
        model.add(sum(row) + int(machine in fixed_machines[service]) <= 1)

    presence_cache: dict[tuple[int, int], cp_model.IntVar] = {}

    def dynamic_presence(service: int, neighborhood: int) -> cp_model.IntVar | int:
        if neighborhood in fixed_neighborhoods[service]:
            return 1
        row = by_service_neighborhood.get((service, neighborhood), [])
        if not row:
            return 0
        key = (service, neighborhood)
        if key not in presence_cache:
            presence = model.new_bool_var(f"n_{service}_{neighborhood}")
            model.add_max_equality(presence, row)
            presence_cache[key] = presence
        return presence_cache[key]

    for service in affected_services:
        service_definition = instance.services[service]
        locations = set(fixed_locations[service])
        locations.update(
            location
            for candidate_service, location in by_service_location
            if candidate_service == service
        )
        location_terms: list[cp_model.IntVar | int] = []
        for location in locations:
            if location in fixed_locations[service]:
                location_terms.append(1)
                continue
            row = by_service_location[service, location]
            presence = model.new_bool_var(f"l_{service}_{location}")
            model.add_max_equality(presence, row)
            location_terms.append(presence)
        model.add(sum(location_terms) >= service_definition.spread_min)

    dependency_services = set(affected_services)
    dependency_services.update(
        service
        for service, service_definition in enumerate(instance.services)
        if any(dependency in affected_services for dependency in service_definition.dependencies)
    )
    for service in dependency_services:
        if perf_counter() >= call_deadline:
            return _empty_call(
                "deadline_during_model",
                started=started,
                assignment_variables=assignment_variable_count,
            )
        service_definition = instance.services[service]
        for dependency in service_definition.dependencies:
            neighborhoods = set(fixed_neighborhoods[service])
            neighborhoods.update(
                neighborhood
                for candidate_service, neighborhood in by_service_neighborhood
                if candidate_service == service
            )
            for neighborhood in neighborhoods:
                left = dynamic_presence(service, neighborhood)
                if isinstance(left, int) and left == 0:
                    continue
                right = dynamic_presence(dependency, neighborhood)
                if isinstance(right, int) and right == 1:
                    continue
                model.add(left <= right)

    objective_terms: list[cp_model.LinearExpr | int] = []
    for machine, machine_definition in enumerate(instance.machines):
        if machine % 64 == 0 and perf_counter() >= call_deadline:
            return _empty_call(
                "deadline_during_model",
                started=started,
                assignment_variables=assignment_variable_count,
            )
        if machine not in affected_machines:
            for resource in range(instance.resource_count):
                objective_terms.append(
                    max(
                        0,
                        fixed_usage[machine][resource]
                        - machine_definition.safety_capacities[resource],
                    )
                    * instance.resources[resource].load_cost_weight
                )
            for balance in instance.balance_costs:
                available_first = (
                    machine_definition.capacities[balance.first_resource]
                    - fixed_usage[machine][balance.first_resource]
                )
                available_second = (
                    machine_definition.capacities[balance.second_resource]
                    - fixed_usage[machine][balance.second_resource]
                )
                objective_terms.append(
                    max(
                        0,
                        balance.target * available_first - available_second,
                    )
                    * balance.weight
                )
            continue
        for resource in range(instance.resource_count):
            upper = max(
                0,
                machine_definition.capacities[resource]
                - machine_definition.safety_capacities[resource],
            )
            excess = model.new_int_var(0, upper, f"load_{machine}_{resource}")
            model.add(
                excess
                >= usage_expressions[machine, resource]
                - machine_definition.safety_capacities[resource]
            )
            objective_terms.append(excess * instance.resources[resource].load_cost_weight)
        for balance_id, balance in enumerate(instance.balance_costs):
            upper = (
                balance.target
                * machine_definition.capacities[balance.first_resource]
            )
            imbalance = model.new_int_var(0, upper, f"balance_{machine}_{balance_id}")
            available_first = (
                machine_definition.capacities[balance.first_resource]
                - usage_expressions[machine, balance.first_resource]
            )
            available_second = (
                machine_definition.capacities[balance.second_resource]
                - usage_expressions[machine, balance.second_resource]
            )
            model.add(
                imbalance >= balance.target * available_first - available_second
            )
            objective_terms.append(imbalance * balance.weight)

    objective_terms.append(fixed_process_move * instance.process_move_cost_weight)
    objective_terms.append(fixed_machine_move * instance.machine_move_cost_weight)
    for (process_id, machine), variable in variables.items():
        process = instance.processes[process_id]
        if machine != original[process_id]:
            objective_terms.append(
                variable * process.move_cost * instance.process_move_cost_weight
            )
        objective_terms.append(
            variable
            * instance.machines[original[process_id]].move_costs[machine]
            * instance.machine_move_cost_weight
        )

    service_move_max = model.new_int_var(
        max(fixed_moved_by_service, default=0),
        instance.process_count,
        "service_move_max",
    )
    for service in affected_services:
        moved_terms = [
            variable
            for (process_id, machine), variable in variables.items()
            if instance.processes[process_id].service == service
            and machine != original[process_id]
        ]
        model.add(
            service_move_max
            >= fixed_moved_by_service[service] + sum(moved_terms)
        )
    objective_terms.append(service_move_max * instance.service_move_cost_weight)
    total_objective = sum(objective_terms)
    model.minimize(total_objective)

    remaining = min(call_deadline, deadline) - perf_counter()
    if remaining <= 0:
        return _empty_call(
            "deadline_before_solve",
            started=started,
            assignment_variables=assignment_variable_count,
        )
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = remaining
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = 1
    status_code = solver.solve(model)
    status = solver.status_name(status_code).lower()
    solver_limit = remaining
    wall_time = perf_counter() - started
    branches = int(solver.num_branches)
    conflicts = int(solver.num_conflicts)
    best_bound = (
        round(solver.best_objective_bound)
        if status_code in (cp_model.FEASIBLE, cp_model.OPTIMAL)
        else None
    )
    if status_code not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return RestrictedRepairCall(
            None,
            None,
            status,
            wall_time,
            solver_limit,
            assignment_variable_count,
            branches,
            conflicts,
            best_bound,
        )

    candidate = list(incumbent)
    for process_id in processes:
        candidate[process_id] = next(
            machine
            for machine in domains[process_id]
            if solver.boolean_value(variables[process_id, machine])
        )
    candidate_assignment = tuple(candidate)
    report = validate(instance, original, candidate_assignment)
    if not report.feasible:  # pragma: no cover - full oracle guard
        return RestrictedRepairCall(
            None,
            None,
            "oracle_rejected",
            wall_time,
            solver_limit,
            assignment_variable_count,
            branches,
            conflicts,
            best_bound,
        )
    candidate_objective = evaluate_objective(instance, original, candidate_assignment)
    incumbent_objective = evaluate_objective(instance, original, incumbent)
    if candidate_objective.total_cost >= incumbent_objective.total_cost:
        return RestrictedRepairCall(
            None,
            None,
            f"{status}_not_improved",
            wall_time,
            solver_limit,
            assignment_variable_count,
            branches,
            conflicts,
            best_bound,
        )
    return RestrictedRepairCall(
        candidate_assignment,
        candidate_objective,
        status,
        wall_time,
        solver_limit,
        assignment_variable_count,
        branches,
        conflicts,
        best_bound,
    )
