"""Run the frozen M6 exact-repair ablation and official checks."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from gmrp_alns.gmrp.checker import run_official_checker
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance, write_assignment
from gmrp_alns.search.alns import adaptive_alns
from gmrp_alns.search.model import SearchResult

COST_PATTERN = re.compile(r"Total objective cost is\s+(\d+)")
VALID_PATTERN = re.compile(r"Solution is valid", re.IGNORECASE)


def _find_model(data_root: Path, name: str) -> Path:
    matches = list(data_root.rglob(f"model_{name}.txt"))
    if len(matches) != 1:
        raise ValueError(f"expected one model for {name}, found {len(matches)}")
    return matches[0]


def _official_check(
    checker: Path,
    model: Path,
    initial: Path,
    output: Path,
    result: SearchResult,
) -> bool:
    write_assignment(output, result.assignment)
    checked = run_official_checker(checker, model, initial, output)
    match = COST_PATTERN.search(checked.stdout)
    cost = int(match.group(1)) if match is not None else None
    return (
        checked.returncode == 0
        and bool(VALID_PATTERN.search(checked.stdout))
        and cost == result.objective.total_cost
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("checker", type=Path)
    parser.add_argument("data_root", type=Path)
    args = parser.parse_args()
    config: dict[str, Any] = json.loads(args.config.read_text(encoding="utf-8"))
    common = config["adaptive_alns"]
    restricted = config["restricted_repair"]
    rows: list[dict[str, object]] = []
    all_official_valid = True
    all_limits_respected = True
    exact_call_count = 0
    exact_improvement_count = 0

    with TemporaryDirectory(prefix="gmrp-m6-") as temporary_directory:
        temporary = Path(temporary_directory)
        for name in config["instances"]:
            model_path = _find_model(args.data_root, name)
            assignment_path = model_path.with_name(
                model_path.name.replace("model_", "assignment_")
            )
            instance = parse_instance(model_path)
            original = parse_assignment(assignment_path, instance)
            for seed in config["seeds"]:
                baseline = adaptive_alns(
                    instance,
                    original,
                    original,
                    time_limit_seconds=config["time_limit_seconds"],
                    seed=seed,
                    **common,
                )
                hybrid = adaptive_alns(
                    instance,
                    original,
                    original,
                    time_limit_seconds=config["time_limit_seconds"],
                    seed=seed,
                    restricted_repair_interval=restricted["interval"],
                    restricted_repair_time_limit_seconds=restricted[
                        "time_limit_seconds"
                    ],
                    restricted_repair_candidate_machines=restricted[
                        "candidate_machine_limit"
                    ],
                    restricted_repair_variable_limit=restricted["variable_limit"],
                    **common,
                )
                baseline_valid = _official_check(
                    args.checker,
                    model_path,
                    assignment_path,
                    temporary / f"{name}_{seed}_baseline.sol",
                    baseline,
                )
                hybrid_valid = _official_check(
                    args.checker,
                    model_path,
                    assignment_path,
                    temporary / f"{name}_{seed}_hybrid.sol",
                    hybrid,
                )
                all_official_valid &= baseline_valid and hybrid_valid
                calls = hybrid.config["restricted_repair"]["calls"]
                exact_call_count += len(calls)
                exact_improvement_count += sum(bool(call["improved"]) for call in calls)
                limits_respected = all(
                    int(call["assignment_variables"]) <= restricted["variable_limit"]
                    and float(call["solver_time_limit_seconds"])
                    <= restricted["time_limit_seconds"]
                    and float(call["wall_time_seconds"])
                    <= restricted["time_limit_seconds"]
                    + restricted["allowed_call_overrun_seconds"]
                    for call in calls
                )
                all_limits_respected &= limits_respected
                rows.append(
                    {
                        "instance": name,
                        "seed": seed,
                        "baseline_cost": baseline.objective.total_cost,
                        "hybrid_cost": hybrid.objective.total_cost,
                        "hybrid_improvement": (
                            baseline.objective.total_cost - hybrid.objective.total_cost
                        ),
                        "baseline_iterations": baseline.iterations,
                        "hybrid_iterations": hybrid.iterations,
                        "exact_calls": len(calls),
                        "exact_improvements": sum(
                            bool(call["improved"]) for call in calls
                        ),
                        "limits_respected": limits_respected,
                        "baseline_official_valid": baseline_valid,
                        "hybrid_official_valid": hybrid_valid,
                    }
                )

    baseline_total = sum(int(row["baseline_cost"]) for row in rows)
    hybrid_total = sum(int(row["hybrid_cost"]) for row in rows)
    payload = {
        "config": str(args.config),
        "pair_count": len(rows),
        "hybrid_wins": sum(int(row["hybrid_improvement"]) > 0 for row in rows),
        "ties": sum(int(row["hybrid_improvement"]) == 0 for row in rows),
        "hybrid_losses": sum(int(row["hybrid_improvement"]) < 0 for row in rows),
        "baseline_total_cost": baseline_total,
        "hybrid_total_cost": hybrid_total,
        "total_improvement": baseline_total - hybrid_total,
        "exact_calls": exact_call_count,
        "exact_improvements": exact_improvement_count,
        "all_limits_respected": all_limits_respected,
        "all_official_valid": all_official_valid,
        "results": rows,
    }
    print(json.dumps(payload, indent=2))
    passed = bool(rows) and exact_call_count > 0 and all_limits_respected
    passed &= all_official_valid
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
