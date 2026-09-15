"""Validate and score all official initial assignments in a downloaded dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance
from gmrp_alns.gmrp.validator import validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    rows: list[dict[str, object]] = []
    failed = False
    for model_path in sorted(args.directory.glob("model_*.txt")):
        assignment_path = model_path.with_name(model_path.name.replace("model_", "assignment_"))
        instance = parse_instance(model_path)
        assignment = parse_assignment(assignment_path, instance)
        report = validate(instance, assignment, assignment)
        objective = evaluate_objective(instance, assignment, assignment)
        failed |= not report.feasible
        rows.append(
            {
                "instance": model_path.stem.removeprefix("model_"),
                "feasible": report.feasible,
                "violations": len(report.violations),
                "initial_cost": objective.total_cost,
                **instance.summary(),
            }
        )
    print(json.dumps(rows, indent=2))
    return 1 if failed or not rows else 0


if __name__ == "__main__":
    raise SystemExit(main())

