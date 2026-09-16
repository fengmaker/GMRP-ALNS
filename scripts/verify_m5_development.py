"""Run the frozen paired M5 development comparison and official checks."""

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
from gmrp_alns.search.lns import random_lns
from gmrp_alns.search.model import SearchResult

COST_PATTERN = re.compile(r"Total objective cost is\s+(\d+)")
VALID_PATTERN = re.compile(r"Solution is valid", re.IGNORECASE)


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


def _find_model(data_root: Path, name: str) -> Path:
    matches = list(data_root.rglob(f"model_{name}.txt"))
    if len(matches) != 1:
        raise ValueError(f"expected one model for {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("checker", type=Path)
    parser.add_argument("data_root", type=Path)
    args = parser.parse_args()
    config: dict[str, Any] = json.loads(args.config.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    all_official_valid = True

    with TemporaryDirectory(prefix="gmrp-m5-") as temporary_directory:
        temporary = Path(temporary_directory)
        for name in config["instances"]:
            model_path = _find_model(args.data_root, name)
            assignment_path = model_path.with_name(
                model_path.name.replace("model_", "assignment_")
            )
            instance = parse_instance(model_path)
            original = parse_assignment(assignment_path, instance)
            for seed in config["seeds"]:
                baseline_config = config["baseline"]
                baseline = random_lns(
                    instance,
                    original,
                    original,
                    repair="greedy",
                    time_limit_seconds=config["time_limit_seconds"],
                    seed=seed,
                    destroy_size=baseline_config["destroy_size"],
                    repair_top_k=baseline_config["repair_top_k"],
                    repair_node_limit=baseline_config["repair_node_limit"],
                )
                adaptive_config = config["adaptive_alns"]
                adaptive = adaptive_alns(
                    instance,
                    original,
                    original,
                    time_limit_seconds=config["time_limit_seconds"],
                    seed=seed,
                    **adaptive_config,
                )
                baseline_valid = _official_check(
                    args.checker,
                    model_path,
                    assignment_path,
                    temporary / f"{name}_{seed}_baseline.sol",
                    baseline,
                )
                adaptive_valid = _official_check(
                    args.checker,
                    model_path,
                    assignment_path,
                    temporary / f"{name}_{seed}_adaptive.sol",
                    adaptive,
                )
                all_official_valid &= baseline_valid and adaptive_valid
                rows.append(
                    {
                        "instance": name,
                        "seed": seed,
                        "baseline_cost": baseline.objective.total_cost,
                        "adaptive_cost": adaptive.objective.total_cost,
                        "adaptive_improvement": (
                            baseline.objective.total_cost
                            - adaptive.objective.total_cost
                        ),
                        "adaptive_wins": (
                            adaptive.objective.total_cost
                            < baseline.objective.total_cost
                        ),
                        "baseline_iterations": baseline.iterations,
                        "adaptive_iterations": adaptive.iterations,
                        "baseline_official_valid": baseline_valid,
                        "adaptive_official_valid": adaptive_valid,
                    }
                )

    wins = sum(bool(row["adaptive_wins"]) for row in rows)
    baseline_total = sum(int(row["baseline_cost"]) for row in rows)
    adaptive_total = sum(int(row["adaptive_cost"]) for row in rows)
    required_wins = int(config["acceptance"]["minimum_paired_wins"])
    stable_improvement = wins >= required_wins and (
        not config["acceptance"]["require_lower_total_cost"]
        or adaptive_total < baseline_total
    )
    payload = {
        "config": str(args.config),
        "pair_count": len(rows),
        "adaptive_wins": wins,
        "baseline_total_cost": baseline_total,
        "adaptive_total_cost": adaptive_total,
        "total_improvement": baseline_total - adaptive_total,
        "stable_improvement": stable_improvement,
        "all_official_valid": all_official_valid,
        "results": rows,
    }
    print(json.dumps(payload, indent=2))
    return 0 if rows and stable_improvement and all_official_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
