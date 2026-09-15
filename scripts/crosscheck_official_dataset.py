"""Compare this project's initial costs with the official checker over a directory."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from gmrp_alns.gmrp.checker import run_official_checker
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance
from gmrp_alns.gmrp.validator import validate

COST_PATTERN = re.compile(r"Total objective cost is\s+(\d+)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checker", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    rows: list[dict[str, object]] = []
    failed = False

    for model_path in sorted(args.directory.glob("model_*.txt")):
        assignment_path = model_path.with_name(model_path.name.replace("model_", "assignment_"))
        instance = parse_instance(model_path)
        assignment = parse_assignment(assignment_path, instance)
        own_report = validate(instance, assignment, assignment)
        own_cost = evaluate_objective(instance, assignment, assignment).total_cost
        official = run_official_checker(
            args.checker, model_path, assignment_path, assignment_path
        )
        match = COST_PATTERN.search(official.stdout)
        official_cost = int(match.group(1)) if match else None
        agrees = own_report.feasible and official.returncode == 0 and official_cost == own_cost
        failed |= not agrees
        rows.append(
            {
                "instance": model_path.stem.removeprefix("model_"),
                "feasible": own_report.feasible,
                "own_cost": own_cost,
                "official_cost": official_cost,
                "agrees": agrees,
            }
        )

    print(json.dumps(rows, indent=2))
    return 1 if failed or not rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
