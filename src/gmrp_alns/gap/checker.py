"""Independent full feasibility and objective evaluation for classic GAP."""

from __future__ import annotations

from dataclasses import dataclass

from gmrp_alns.gap.model import GapAssignment, GapInstance


@dataclass(frozen=True, slots=True)
class GapValidation:
    feasible: bool
    objective: int | None
    usage: tuple[int, ...]
    violations: tuple[str, ...]


def evaluate_assignment(instance: GapInstance, assignment: GapAssignment) -> GapValidation:
    violations: list[str] = []
    if len(assignment) != instance.job_count:
        return GapValidation(
            feasible=False,
            objective=None,
            usage=tuple(0 for _ in range(instance.agent_count)),
            violations=(
                f"assignment contains {len(assignment)} jobs; expected {instance.job_count}",
            ),
        )

    usage = [0] * instance.agent_count
    objective = 0
    valid_indices = True
    for job, agent in enumerate(assignment):
        if not 0 <= agent < instance.agent_count:
            violations.append(
                f"assignment[{job}] agent {agent} is outside [0, {instance.agent_count})"
            )
            valid_indices = False
            continue
        usage[agent] += instance.resources[agent][job]
        objective += instance.costs[agent][job]
    if valid_indices:
        for agent, (actual, capacity) in enumerate(
            zip(usage, instance.capacities, strict=True)
        ):
            if actual > capacity:
                violations.append(
                    f"agent {agent} uses {actual}, exceeding capacity {capacity}"
                )
    return GapValidation(
        feasible=not violations,
        objective=objective if valid_indices else None,
        usage=tuple(usage),
        violations=tuple(violations),
    )
