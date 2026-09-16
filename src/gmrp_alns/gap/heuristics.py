"""Feasible construction, repair, relocate, and swap baselines for classic GAP."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from time import monotonic, perf_counter
from typing import Literal

from gmrp_alns.gap.checker import evaluate_assignment
from gmrp_alns.gap.model import GapAssignment, GapInstance, GapSolveResult

ConstructionStrategy = Literal["cost", "regret"]


@dataclass(frozen=True, slots=True)
class LocalSearchOutcome:
    assignment: GapAssignment
    objective: int
    iterations: int
    candidate_evaluations: int


def _is_better(instance: GapInstance, candidate: int, incumbent: int) -> bool:
    if instance.sense == "minimize":
        return candidate < incumbent
    return candidate > incumbent


def _desirability_key(instance: GapInstance, cost: int, agent: int) -> tuple[int, int]:
    return (cost, -agent) if instance.sense == "maximize" else (-cost, -agent)


def repair_assignment(
    instance: GapInstance,
    partial_assignment: Sequence[int | None],
    *,
    strategy: ConstructionStrategy = "regret",
    seed: int = 0,
    attempts: int = 16,
    time_limit_seconds: float | None = None,
) -> GapAssignment | None:
    """Complete a capacity-feasible partial assignment with deterministic restarts.

    Already assigned jobs remain fixed.  ``None`` denotes an unassigned job.  A failed
    repair returns ``None`` instead of exposing an infeasible candidate.
    """

    if strategy not in ("cost", "regret"):
        raise ValueError(f"unknown construction strategy: {strategy}")
    if len(partial_assignment) != instance.job_count:
        raise ValueError(
            f"partial assignment has {len(partial_assignment)} jobs; expected {instance.job_count}"
        )
    if attempts <= 0:
        raise ValueError("attempts must be positive")
    if time_limit_seconds is not None and time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    deadline = None if time_limit_seconds is None else monotonic() + time_limit_seconds

    fixed_usage = [0] * instance.agent_count
    unassigned: list[int] = []
    base = list(partial_assignment)
    for job, agent in enumerate(base):
        if agent is None:
            unassigned.append(job)
            continue
        if not 0 <= agent < instance.agent_count:
            raise ValueError(f"partial assignment[{job}] has invalid agent {agent}")
        fixed_usage[agent] += instance.resources[agent][job]
    if any(
        used > capacity
        for used, capacity in zip(fixed_usage, instance.capacities, strict=True)
    ):
        return None

    rng = random.Random(seed)
    for attempt in range(attempts):
        if deadline is not None and monotonic() >= deadline:
            break
        assignment = base.copy()
        usage = fixed_usage.copy()
        remaining = unassigned.copy()
        if attempt:
            rng.shuffle(remaining)

        while remaining:
            candidates: list[tuple[tuple[int, int, int, int], int, int]] = []
            impossible = False
            for order, job in enumerate(remaining):
                feasible_agents = [
                    agent
                    for agent in range(instance.agent_count)
                    if usage[agent] + instance.resources[agent][job]
                    <= instance.capacities[agent]
                ]
                if not feasible_agents:
                    impossible = True
                    break
                feasible_agents.sort(
                    key=lambda agent: _desirability_key(
                        instance, instance.costs[agent][job], agent
                    ),
                    reverse=True,
                )
                best = feasible_agents[0]
                best_cost = instance.costs[best][job]
                if strategy == "regret":
                    second_cost = (
                        instance.costs[feasible_agents[1]][job]
                        if len(feasible_agents) > 1
                        else best_cost
                    )
                    regret = (
                        second_cost - best_cost
                        if instance.sense == "minimize"
                        else best_cost - second_cost
                    )
                    priority = (regret, -len(feasible_agents), -order, -job)
                else:
                    signed_cost = best_cost if instance.sense == "maximize" else -best_cost
                    priority = (-len(feasible_agents), signed_cost, -order, -job)
                candidates.append((priority, job, best))
            if impossible:
                break
            _, selected_job, selected_agent = max(candidates)
            assignment[selected_job] = selected_agent
            usage[selected_agent] += instance.resources[selected_agent][selected_job]
            remaining.remove(selected_job)

        if not remaining:
            completed = tuple(agent for agent in assignment if agent is not None)
            if len(completed) != instance.job_count:  # pragma: no cover - defensive guard
                raise AssertionError("repair lost an assignment entry")
            validation = evaluate_assignment(instance, completed)
            if validation.feasible:
                return completed
    return _backtracking_repair(
        instance,
        base,
        fixed_usage,
        unassigned,
        strategy=strategy,
        deadline=deadline,
    )


def _backtracking_repair(
    instance: GapInstance,
    base: list[int | None],
    fixed_usage: list[int],
    unassigned: list[int],
    *,
    strategy: ConstructionStrategy,
    deadline: float | None,
    node_limit: int = 500_000,
) -> GapAssignment | None:
    """Bounded fail-first repair used only after greedy restarts dead-end."""

    assignment = base.copy()
    usage = fixed_usage.copy()
    remaining = set(unassigned)
    nodes = 0

    def search() -> bool:
        nonlocal nodes
        nodes += 1
        if nodes > node_limit or (deadline is not None and monotonic() >= deadline):
            return False
        if not remaining:
            return True

        selected_job = -1
        selected_agents: list[int] = []
        selected_priority: tuple[float, ...] | None = None
        for job in remaining:
            feasible_agents = [
                agent
                for agent in range(instance.agent_count)
                if usage[agent] + instance.resources[agent][job]
                <= instance.capacities[agent]
            ]
            if not feasible_agents:
                return False
            feasible_agents.sort(
                key=lambda agent: _desirability_key(
                    instance, instance.costs[agent][job], agent
                ),
                reverse=True,
            )
            best_cost = instance.costs[feasible_agents[0]][job]
            second_cost = (
                instance.costs[feasible_agents[1]][job]
                if len(feasible_agents) > 1
                else best_cost
            )
            regret = (
                second_cost - best_cost
                if instance.sense == "minimize"
                else best_cost - second_cost
            )
            tightness = min(
                instance.resources[agent][job] / max(1, instance.capacities[agent] - usage[agent])
                for agent in feasible_agents
            )
            priority = (
                -float(len(feasible_agents)),
                float(regret if strategy == "regret" else 0),
                tightness,
                -float(job),
            )
            if selected_priority is None or priority > selected_priority:
                selected_priority = priority
                selected_job = job
                selected_agents = feasible_agents

        remaining.remove(selected_job)
        for agent in selected_agents:
            assignment[selected_job] = agent
            usage[agent] += instance.resources[agent][selected_job]
            if search():
                return True
            usage[agent] -= instance.resources[agent][selected_job]
            assignment[selected_job] = None
        remaining.add(selected_job)
        return False

    if not search():
        return None
    completed = tuple(agent for agent in assignment if agent is not None)
    if len(completed) != instance.job_count:  # pragma: no cover - defensive guard
        raise AssertionError("backtracking repair lost an assignment entry")
    return completed


def improve_relocate(
    instance: GapInstance,
    assignment: GapAssignment,
    *,
    deadline: float | None = None,
) -> LocalSearchOutcome:
    """Apply best-improvement feasible relocate moves until local optimality."""

    validation = evaluate_assignment(instance, assignment)
    if not validation.feasible or validation.objective is None:
        raise ValueError(f"relocate requires a feasible assignment: {validation.violations}")
    current = list(assignment)
    usage = list(validation.usage)
    objective = validation.objective
    iterations = 0
    evaluations = 0
    while True:
        if deadline is not None and monotonic() >= deadline:
            break
        best_move: tuple[int, int, int] | None = None
        best_objective = objective
        for job, old_agent in enumerate(current):
            for new_agent in range(instance.agent_count):
                if deadline is not None and monotonic() >= deadline:
                    return LocalSearchOutcome(
                        tuple(current), objective, iterations, evaluations
                    )
                if new_agent == old_agent:
                    continue
                evaluations += 1
                if (
                    usage[new_agent] + instance.resources[new_agent][job]
                    > instance.capacities[new_agent]
                ):
                    continue
                candidate_objective = (
                    objective
                    - instance.costs[old_agent][job]
                    + instance.costs[new_agent][job]
                )
                if _is_better(instance, candidate_objective, best_objective):
                    best_objective = candidate_objective
                    best_move = (job, old_agent, new_agent)
        if best_move is None:
            break
        job, old_agent, new_agent = best_move
        usage[old_agent] -= instance.resources[old_agent][job]
        usage[new_agent] += instance.resources[new_agent][job]
        current[job] = new_agent
        objective = best_objective
        iterations += 1
    return LocalSearchOutcome(tuple(current), objective, iterations, evaluations)


def improve_swap(
    instance: GapInstance,
    assignment: GapAssignment,
    *,
    deadline: float | None = None,
) -> LocalSearchOutcome:
    """Apply best-improvement feasible two-job swaps until local optimality."""

    validation = evaluate_assignment(instance, assignment)
    if not validation.feasible or validation.objective is None:
        raise ValueError(f"swap requires a feasible assignment: {validation.violations}")
    current = list(assignment)
    usage = list(validation.usage)
    objective = validation.objective
    iterations = 0
    evaluations = 0
    while True:
        if deadline is not None and monotonic() >= deadline:
            break
        best_move: tuple[int, int, int, int] | None = None
        best_objective = objective
        for first_job in range(instance.job_count):
            first_agent = current[first_job]
            for second_job in range(first_job + 1, instance.job_count):
                if deadline is not None and monotonic() >= deadline:
                    return LocalSearchOutcome(
                        tuple(current), objective, iterations, evaluations
                    )
                second_agent = current[second_job]
                if first_agent == second_agent:
                    continue
                evaluations += 1
                first_usage = (
                    usage[first_agent]
                    - instance.resources[first_agent][first_job]
                    + instance.resources[first_agent][second_job]
                )
                second_usage = (
                    usage[second_agent]
                    - instance.resources[second_agent][second_job]
                    + instance.resources[second_agent][first_job]
                )
                if (
                    first_usage > instance.capacities[first_agent]
                    or second_usage > instance.capacities[second_agent]
                ):
                    continue
                candidate_objective = (
                    objective
                    - instance.costs[first_agent][first_job]
                    - instance.costs[second_agent][second_job]
                    + instance.costs[first_agent][second_job]
                    + instance.costs[second_agent][first_job]
                )
                if _is_better(instance, candidate_objective, best_objective):
                    best_objective = candidate_objective
                    best_move = (first_job, second_job, first_agent, second_agent)
        if best_move is None:
            break
        first_job, second_job, first_agent, second_agent = best_move
        usage[first_agent] = (
            usage[first_agent]
            - instance.resources[first_agent][first_job]
            + instance.resources[first_agent][second_job]
        )
        usage[second_agent] = (
            usage[second_agent]
            - instance.resources[second_agent][second_job]
            + instance.resources[second_agent][first_job]
        )
        current[first_job], current[second_job] = second_agent, first_agent
        objective = best_objective
        iterations += 1
    return LocalSearchOutcome(tuple(current), objective, iterations, evaluations)


def _construct_result(
    instance: GapInstance,
    *,
    strategy: ConstructionStrategy,
    seed: int,
    time_limit_seconds: float,
    local_search: bool,
) -> GapSolveResult:
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    started = perf_counter()
    assignment = repair_assignment(
        instance,
        [None] * instance.job_count,
        strategy=strategy,
        seed=seed,
        time_limit_seconds=time_limit_seconds,
    )
    iterations = 0
    evaluations = 0
    if assignment is not None and local_search:
        remaining_seconds = max(0.0, time_limit_seconds - (perf_counter() - started))
        deadline = monotonic() + remaining_seconds
        relocate = improve_relocate(instance, assignment, deadline=deadline)
        swap = improve_swap(instance, relocate.assignment, deadline=deadline)
        assignment = swap.assignment
        iterations = relocate.iterations + swap.iterations
        evaluations = relocate.candidate_evaluations + swap.candidate_evaluations
    elapsed = perf_counter() - started
    validation = None if assignment is None else evaluate_assignment(instance, assignment)
    if validation is not None and not validation.feasible:  # pragma: no cover - oracle guard
        raise AssertionError(f"heuristic exposed an infeasible result: {validation.violations}")
    objective = None if validation is None else validation.objective
    return GapSolveResult(
        algorithm=f"{strategy}-greedy" + ("-relocate-swap" if local_search else ""),
        status="feasible" if assignment is not None else "repair_failed",
        assignment=assignment,
        objective=objective,
        best_bound=None,
        optimal=False,
        wall_time_seconds=elapsed,
        time_to_best_seconds=elapsed,
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        iterations=iterations,
        candidate_evaluations=evaluations,
    )


def cost_greedy(
    instance: GapInstance,
    *,
    seed: int = 0,
    time_limit_seconds: float = 60.0,
    local_search: bool = True,
) -> GapSolveResult:
    return _construct_result(
        instance,
        strategy="cost",
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        local_search=local_search,
    )


def regret_greedy(
    instance: GapInstance,
    *,
    seed: int = 0,
    time_limit_seconds: float = 60.0,
    local_search: bool = True,
) -> GapSolveResult:
    return _construct_result(
        instance,
        strategy="regret",
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        local_search=local_search,
    )
