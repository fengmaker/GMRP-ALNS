"""Result and telemetry objects shared by GMRP search algorithms."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from gmrp_alns.gmrp.model import Assignment
from gmrp_alns.gmrp.objective import ObjectiveBreakdown


@dataclass(frozen=True, slots=True)
class TracePoint:
    elapsed_seconds: float
    iteration: int
    current_cost: int
    best_cost: int
    operator: str
    current_objective: ObjectiveBreakdown | None = None
    objective_component_delta: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["current_objective_components"] = (
            self.current_objective.as_dict() if self.current_objective is not None else None
        )
        payload.pop("current_objective")
        return payload


@dataclass(frozen=True, slots=True)
class OperatorStats:
    calls: int
    successes: int
    candidate_evaluations: int
    total_improvement: int
    wall_time_seconds: float
    accepted: int = 0
    new_best: int = 0
    failures: int = 0
    final_weight: float | None = None
    weight_updates: int = 0

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SearchResult:
    algorithm: str
    assignment: Assignment
    objective: ObjectiveBreakdown
    initial_cost: int
    seed: int
    time_limit_seconds: float
    wall_time_seconds: float
    time_to_best_seconds: float
    iterations: int
    candidate_evaluations: int
    moved_processes: int
    trace: tuple[TracePoint, ...]
    operator_stats: dict[str, OperatorStats]
    config: dict[str, Any]

    def as_dict(self, instance_name: str) -> dict[str, Any]:
        return {
            "instance": instance_name,
            "problem": "gmrp",
            "algorithm": self.algorithm,
            "seed": self.seed,
            "time_limit_seconds": self.time_limit_seconds,
            "feasible": True,
            "initial_cost": self.initial_cost,
            "best_cost": self.objective.total_cost,
            "time_to_best_seconds": self.time_to_best_seconds,
            "iterations": self.iterations,
            "candidate_evaluations": self.candidate_evaluations,
            "moved_processes": self.moved_processes,
            "objective_components": self.objective.as_dict(),
            "operator_stats": {
                name: stats.as_dict() for name, stats in self.operator_stats.items()
            },
            "convergence_trace": [point.as_dict() for point in self.trace],
            "wall_time_seconds": self.wall_time_seconds,
            "peak_memory_mb": None,
            "git_commit": None,
            "assignment": list(self.assignment),
            "config": self.config,
        }
