"""Run an M4 search over official A instances and cross-check every result."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from gmrp_alns.gmrp.checker import run_official_checker
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance, write_assignment
from gmrp_alns.gmrp.validator import validate
from gmrp_alns.search.local_search import relocate_search, vnd_search

COST_PATTERN = re.compile(r"Total objective cost is\s+(\d+)")
VALID_PATTERN = re.compile(r"Solution is valid", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checker", type=Path)
    parser.add_argument("directories", type=Path, nargs="+")
    parser.add_argument(
        "--algorithm",
        choices=("relocate-first", "relocate-best", "vnd-first", "vnd-best"),
        default="vnd-first",
    )
    parser.add_argument("--time-limit", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-iterations", type=int)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--max-swap-candidates", type=int, default=5_000)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    failed = False
    improved_count = 0
    with TemporaryDirectory(prefix="gmrp-m4-") as temporary_directory:
        output_directory = Path(temporary_directory)
        for directory in args.directories:
            for model_path in sorted(directory.glob("model_*.txt")):
                assignment_path = model_path.with_name(
                    model_path.name.replace("model_", "assignment_")
                )
                instance = parse_instance(model_path)
                original = parse_assignment(assignment_path, instance)
                common = {
                    "time_limit_seconds": args.time_limit,
                    "seed": args.seed,
                    "max_iterations": args.max_iterations,
                    "top_k": args.top_k,
                }
                if args.algorithm.startswith("relocate-"):
                    result = relocate_search(
                        instance,
                        original,
                        original,
                        strategy=args.algorithm.removeprefix("relocate-"),
                        **common,
                    )
                else:
                    result = vnd_search(
                        instance,
                        original,
                        original,
                        strategy=args.algorithm.removeprefix("vnd-"),
                        max_swap_candidates=args.max_swap_candidates,
                        **common,
                    )

                self_report = validate(instance, original, result.assignment)
                self_cost = evaluate_objective(
                    instance, original, result.assignment
                ).total_cost
                output_path = output_directory / f"solution_{model_path.stem}.txt"
                write_assignment(output_path, result.assignment)
                official = run_official_checker(
                    args.checker,
                    model_path,
                    assignment_path,
                    output_path,
                )
                official_match = COST_PATTERN.search(official.stdout)
                official_cost = (
                    int(official_match.group(1)) if official_match is not None else None
                )
                official_valid = bool(VALID_PATTERN.search(official.stdout))
                agrees = (
                    self_report.feasible
                    and official.returncode == 0
                    and official_valid
                    and official_cost == self_cost == result.objective.total_cost
                )
                failed |= not agrees
                improved_count += int(result.objective.total_cost < result.initial_cost)
                rows.append(
                    {
                        "instance": model_path.stem.removeprefix("model_"),
                        "initial_cost": result.initial_cost,
                        "best_cost": result.objective.total_cost,
                        "improvement": result.initial_cost - result.objective.total_cost,
                        "iterations": result.iterations,
                        "candidate_evaluations": result.candidate_evaluations,
                        "time_to_best_seconds": result.time_to_best_seconds,
                        "wall_time_seconds": result.wall_time_seconds,
                        "self_feasible": self_report.feasible,
                        "official_valid": official_valid,
                        "official_cost": official_cost,
                        "agrees": agrees,
                    }
                )

    majority_improved = improved_count > len(rows) // 2
    payload = {
        "algorithm": args.algorithm,
        "seed": args.seed,
        "time_limit_seconds": args.time_limit,
        "instance_count": len(rows),
        "improved_count": improved_count,
        "majority_improved": majority_improved,
        "all_self_feasible": all(row["self_feasible"] for row in rows),
        "all_official_valid": all(row["official_valid"] for row in rows),
        "all_costs_agree": all(row["agrees"] for row in rows),
        "results": rows,
    }
    print(json.dumps(payload, indent=2))
    return 1 if failed or not rows or not majority_improved else 0


if __name__ == "__main__":
    raise SystemExit(main())
