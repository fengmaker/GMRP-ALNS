"""One fresh process per observation, including independent final checking."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

import psutil

from gmrp_alns.gmrp.checker import run_official_checker
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance, write_assignment
from gmrp_alns.gmrp.validator import validate
from gmrp_alns.search.alns import adaptive_alns
from gmrp_alns.search.lns import random_lns
from gmrp_alns.search.local_search import relocate_search, vnd_search


def execute(job: dict[str, Any], root: Path, solution: Path) -> dict[str, Any]:
    spec = job["input"]
    started = perf_counter()
    instance = parse_instance(root / spec["model"])
    original = parse_assignment(root / spec["initial"], instance)
    parse_seconds = perf_counter() - started
    method = job["method"]
    common = dict(time_limit_seconds=job["budget"], seed=job["seed"])
    started = perf_counter()
    if method == "initial":
        assignment = original
        objective = evaluate_objective(instance, original, original)
        payload: dict[str, Any] = {
            "initial_cost": objective.total_cost, "best_cost": objective.total_cost,
            "objective_components": objective.as_dict(), "time_to_best_seconds": 0.0,
            "iterations": 0, "candidate_evaluations": 0, "operator_stats": {},
            "convergence_trace": [{"elapsed_seconds": 0.0, "best_cost": objective.total_cost}],
            "config": {}, "moved_processes": 0,
        }
    else:
        if method == "relocate":
            result = relocate_search(instance, original, original, **common)
        elif method == "vnd":
            result = vnd_search(instance, original, original, **common)
        elif method == "random-lns":
            result = random_lns(instance, original, original, **common)
        else:
            options = dict(job["alns"])
            if method == "restricted":
                options.update(job["restricted"])
            elif method == "random-only":
                options["destroy_operators"] = ("random",)
            elif method == "no-restart":
                options["restart_interval"] = 0
            elif method == "greedy-only":
                options["repair_operators"] = ("greedy",)
            result = adaptive_alns(instance, original, original, **common, **options)
        # Include the solver's full-oracle handoff in externally observed solver time.
        solver_seconds = perf_counter() - started
        assignment = result.assignment
        payload = result.as_dict(job["instance"])
        payload["solver_seconds"] = solver_seconds
        payload.pop("assignment")
        # Retain exact best-so-far change points; accepted non-best states are not needed
        # for this protocol's convergence metric. Record this projection in the manifest.
        best = None
        trajectory = []
        for point in result.trace:
            if best is None or point.best_cost < best:
                trajectory.append({"elapsed_seconds": point.elapsed_seconds,
                                   "best_cost": point.best_cost})
                best = point.best_cost
        payload["convergence_trace"] = trajectory
        payload["config"].pop("weight_trace", None)
    payload.setdefault("solver_seconds", perf_counter() - started)
    checked_at = perf_counter()
    report = validate(instance, original, assignment)
    objective = evaluate_objective(instance, original, assignment)
    if not report.feasible or objective.total_cost != payload["best_cost"]:
        raise ValueError("full oracle rejected solver result")
    write_assignment(solution, assignment)
    checked = run_official_checker(
        root / job["checker"], root / spec["model"], root / spec["initial"], solution,
        timeout_seconds=120,
    )
    cost = re.search(r"Total objective cost is\s+(\d+)", checked.stdout)
    official_valid = (
        checked.returncode == 0 and "solution is valid" in checked.stdout.lower()
        and cost is not None and int(cost[1]) == objective.total_cost
    )
    payload.update({
        "parse_seconds": parse_seconds,
        "verification_seconds": perf_counter() - checked_at,
        "dimensions": instance.summary(), "feasible": report.feasible,
        "official_valid": official_valid, "checker_stdout": checked.stdout,
        "checker_stderr": checked.stderr, "checker_returncode": checked.returncode,
        "status": "ok" if official_valid else "checker_failed",
    })
    memory = psutil.Process().memory_info()
    payload["worker_peak_memory_mb"] = getattr(memory, "peak_wset", memory.rss) / 2**20
    return payload


def main() -> None:
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path.cwd()
    output = Path(sys.argv[2])
    try:
        payload = execute(job, root, output.with_suffix(".sol"))
    except Exception as exc:
        payload = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    main()
