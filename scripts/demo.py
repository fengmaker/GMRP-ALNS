"""Run the complete offline toy workflow as a deterministic release smoke test."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOY = ROOT / "data" / "toy"


def run_cli(*arguments: str) -> dict[str, Any]:
    command = [sys.executable, "-m", "gmrp_alns", *arguments]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    payload: dict[str, Any] = json.loads(completed.stdout)
    return payload


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    model = str(TOY / "model_toy.txt")
    initial = str(TOY / "assignment_toy.txt")
    reference_solution = str(TOY / "solution_toy.txt")

    parsed = run_cli("parse", model)
    require(parsed["processes"] == 3 and parsed["machines"] == 4, "unexpected toy dimensions")

    validation = run_cli("validate", model, initial, reference_solution)
    require(validation["feasible"], "reference toy solution is infeasible")

    score = run_cli("score", model, initial, reference_solution)
    require(score["objective"]["total_cost"] == 2411, "unexpected toy reference cost")

    with tempfile.TemporaryDirectory(prefix="gmrp-alns-demo-") as directory:
        candidate = Path(directory) / "candidate.sol"
        search = run_cli(
            "solve",
            model,
            initial,
            "--algorithm",
            "adaptive-alns-restricted",
            "--time-limit",
            "2",
            "--max-iterations",
            "20",
            "--seed",
            "42",
            "--output",
            str(candidate),
        )
        require(search["feasible"], "search returned an infeasible solution")
        require(search["best_cost"] == 2411, "search did not reproduce toy cost 2411")
        candidate_validation = run_cli("validate", model, initial, str(candidate))
        require(candidate_validation["feasible"], "written candidate failed validation")

    gap = run_cli(
        "gap",
        "solve",
        str(TOY / "gap_toy.txt"),
        "--sense",
        "minimize",
        "--algorithm",
        "exact",
        "--reference-value",
        "8",
        "--seed",
        "42",
    )
    require(gap["feasible"] and gap["optimal"], "GAP exact baseline did not prove optimality")
    require(gap["matches_reference"], "GAP exact baseline did not reproduce reference value 8")

    print(
        json.dumps(
            {
                "status": "ok",
                "gmrp_dimensions": {
                    "resources": parsed["resources"],
                    "machines": parsed["machines"],
                    "services": parsed["services"],
                    "processes": parsed["processes"],
                },
                "gmrp_reference_cost": score["objective"]["total_cost"],
                "gmrp_search_cost": search["best_cost"],
                "gmrp_candidate_revalidated": candidate_validation["feasible"],
                "gap_reference_cost": gap["best_cost"],
                "gap_optimal": gap["optimal"],
                "seed": 42,
                "max_iterations": 20,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
