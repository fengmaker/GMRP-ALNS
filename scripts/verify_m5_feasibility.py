"""Run Adaptive ALNS over directories and cross-check every final assignment."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from gmrp_alns.gmrp.checker import run_official_checker
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance, write_assignment
from gmrp_alns.search.alns import adaptive_alns

COST_PATTERN = re.compile(r"Total objective cost is\s+(\d+)")
VALID_PATTERN = re.compile(r"Solution is valid", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checker", type=Path)
    parser.add_argument("directories", type=Path, nargs="+")
    parser.add_argument("--time-limit", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-iterations", type=int)
    parser.add_argument("--destroy-size", type=int, default=10)
    parser.add_argument(
        "--instances",
        nargs="+",
        help="optional model suffixes such as b_1 b_2",
    )
    args = parser.parse_args()
    rows: list[dict[str, object]] = []
    failed = False

    with TemporaryDirectory(prefix="gmrp-m5-feasible-") as temporary_directory:
        temporary = Path(temporary_directory)
        for directory in args.directories:
            for model_path in sorted(directory.glob("model_*.txt")):
                instance_name = model_path.stem.removeprefix("model_")
                if args.instances is not None and instance_name not in args.instances:
                    continue
                assignment_path = model_path.with_name(
                    model_path.name.replace("model_", "assignment_")
                )
                instance = parse_instance(model_path)
                original = parse_assignment(assignment_path, instance)
                result = adaptive_alns(
                    instance,
                    original,
                    original,
                    time_limit_seconds=args.time_limit,
                    seed=args.seed,
                    max_iterations=args.max_iterations,
                    destroy_size=args.destroy_size,
                )
                output = temporary / f"solution_{model_path.stem}.txt"
                write_assignment(output, result.assignment)
                checked = run_official_checker(
                    args.checker,
                    model_path,
                    assignment_path,
                    output,
                    timeout_seconds=120,
                )
                match = COST_PATTERN.search(checked.stdout)
                official_cost = int(match.group(1)) if match is not None else None
                valid = (
                    checked.returncode == 0
                    and bool(VALID_PATTERN.search(checked.stdout))
                    and official_cost == result.objective.total_cost
                )
                failed |= not valid
                rows.append(
                    {
                        "instance": instance_name,
                        "initial_cost": result.initial_cost,
                        "best_cost": result.objective.total_cost,
                        "improvement": result.initial_cost - result.objective.total_cost,
                        "iterations": result.iterations,
                        "wall_time_seconds": result.wall_time_seconds,
                        "official_cost": official_cost,
                        "official_valid": valid,
                    }
                )

    payload = {
        "algorithm": "adaptive-alns",
        "seed": args.seed,
        "time_limit_seconds": args.time_limit,
        "instance_count": len(rows),
        "improved_count": sum(int(row["improvement"]) > 0 for row in rows),
        "all_official_valid": all(bool(row["official_valid"]) for row in rows),
        "results": rows,
    }
    print(json.dumps(payload, indent=2))
    return 1 if failed or not rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
