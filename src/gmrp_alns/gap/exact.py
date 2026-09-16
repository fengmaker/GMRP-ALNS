"""OR-Tools CP-SAT exact baseline for small classic GAP instances."""

from __future__ import annotations

from time import perf_counter

from ortools.sat.python import cp_model

from gmrp_alns.gap.checker import evaluate_assignment
from gmrp_alns.gap.model import GapInstance, GapSolveResult


def solve_exact(
    instance: GapInstance,
    *,
    time_limit_seconds: float = 60.0,
    seed: int = 0,
) -> GapSolveResult:
    """Solve one GAP instance with a deterministic single-worker CP-SAT model."""

    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    started = perf_counter()
    model = cp_model.CpModel()
    variables = [
        [model.new_bool_var(f"x_{agent}_{job}") for job in range(instance.job_count)]
        for agent in range(instance.agent_count)
    ]
    for job in range(instance.job_count):
        model.add_exactly_one(variables[agent][job] for agent in range(instance.agent_count))
    for agent in range(instance.agent_count):
        model.add(
            sum(
                instance.resources[agent][job] * variables[agent][job]
                for job in range(instance.job_count)
            )
            <= instance.capacities[agent]
        )
    objective = sum(
        instance.costs[agent][job] * variables[agent][job]
        for agent in range(instance.agent_count)
        for job in range(instance.job_count)
    )
    if instance.sense == "minimize":
        model.minimize(objective)
    else:
        model.maximize(objective)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.random_seed = seed
    solver.parameters.num_search_workers = 1
    status_code = solver.solve(model)
    elapsed = perf_counter() - started
    status = solver.status_name(status_code).lower()
    if status_code not in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return GapSolveResult(
            algorithm="cp-sat",
            status=status,
            assignment=None,
            objective=None,
            best_bound=None,
            optimal=False,
            wall_time_seconds=elapsed,
            time_to_best_seconds=elapsed,
            seed=seed,
            time_limit_seconds=time_limit_seconds,
        )

    assignment = tuple(
        next(
            agent
            for agent in range(instance.agent_count)
            if solver.boolean_value(variables[agent][job])
        )
        for job in range(instance.job_count)
    )
    validation = evaluate_assignment(instance, assignment)
    if not validation.feasible or validation.objective is None:  # pragma: no cover - oracle guard
        raise RuntimeError(f"CP-SAT returned an invalid assignment: {validation.violations}")
    return GapSolveResult(
        algorithm="cp-sat",
        status=status,
        assignment=assignment,
        objective=validation.objective,
        best_bound=round(solver.best_objective_bound),
        optimal=status_code == cp_model.OPTIMAL,
        wall_time_seconds=elapsed,
        time_to_best_seconds=elapsed,
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        candidate_evaluations=int(solver.num_branches),
    )
