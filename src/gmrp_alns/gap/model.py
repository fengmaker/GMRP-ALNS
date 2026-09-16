"""Domain objects shared by the classic GAP implementations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, TypeAlias

GapAssignment: TypeAlias = tuple[int, ...]
ObjectiveSense: TypeAlias = Literal["minimize", "maximize"]


@dataclass(frozen=True, slots=True)
class GapInstance:
    """One OR-Library-style GAP instance.

    Matrices are indexed as ``[agent][job]``.  The objective direction is explicit
    because OR-Library's gap1--gap12 are maximization instances while gapa--gapd are
    minimization instances.
    """

    costs: tuple[tuple[int, ...], ...]
    resources: tuple[tuple[int, ...], ...]
    capacities: tuple[int, ...]
    sense: ObjectiveSense
    name: str
    reference_optimum: int | None = None

    def __post_init__(self) -> None:
        if self.sense not in ("minimize", "maximize"):
            raise ValueError(f"unsupported objective sense: {self.sense!r}")
        if not self.costs:
            raise ValueError("a GAP instance must contain at least one agent")
        if len(self.resources) != len(self.costs) or len(self.capacities) != len(self.costs):
            raise ValueError("cost, resource, and capacity agent dimensions differ")
        job_count = len(self.costs[0])
        if job_count == 0:
            raise ValueError("a GAP instance must contain at least one job")
        for agent, (cost_row, resource_row, capacity) in enumerate(
            zip(self.costs, self.resources, self.capacities, strict=True)
        ):
            if len(cost_row) != job_count or len(resource_row) != job_count:
                raise ValueError(f"agent {agent} row has an inconsistent job dimension")
            if capacity < 0 or any(value < 0 for value in resource_row):
                raise ValueError("resource consumptions and capacities must be non-negative")

    @property
    def agent_count(self) -> int:
        return len(self.costs)

    @property
    def job_count(self) -> int:
        return len(self.costs[0])

    def summary(self) -> dict[str, int | str | None]:
        return {
            "name": self.name,
            "agents": self.agent_count,
            "jobs": self.job_count,
            "sense": self.sense,
            "reference_optimum": self.reference_optimum,
        }


@dataclass(frozen=True, slots=True)
class GapSolveResult:
    """Solver-neutral result record used by exact and heuristic baselines."""

    algorithm: str
    status: str
    assignment: GapAssignment | None
    objective: int | None
    best_bound: int | None
    optimal: bool
    wall_time_seconds: float
    time_to_best_seconds: float
    seed: int
    time_limit_seconds: float
    iterations: int = 0
    candidate_evaluations: int = 0

    @property
    def feasible(self) -> bool:
        return self.assignment is not None and self.objective is not None

    def as_dict(self, instance: GapInstance) -> dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "instance": instance.name,
                "problem": "gap",
                "feasible": self.feasible,
                "initial_cost": None,
                "best_cost": self.objective,
                "moved_processes": 0,
                "objective_components": {"assignment_cost": self.objective},
                "operator_stats": {},
                "git_commit": None,
                "config": {"sense": instance.sense},
            }
        )
        return payload
