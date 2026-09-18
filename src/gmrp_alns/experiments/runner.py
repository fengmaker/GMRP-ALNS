"""Freeze a protocol before serial, isolated execution; preserve all failures."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import psutil

from gmrp_alns.experiments.protocol import (
    digest,
    git_commit,
    identity,
    load_config,
    locate_inputs,
    matrix,
    source_digest,
)


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "cpu": platform.processor(), "logical_cpus": os.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "ram_bytes": psutil.virtual_memory().total,
        "packages": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
            if d.metadata["Name"].lower() not in {"gmrp-alns"}
        },
        "threads": 1, "parallel_runs": 1,
    }


def save(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def freeze(config_path: Path, output: Path, root: Path, checker: Path) -> dict[str, Any]:
    config = load_config(config_path)
    checker = checker.resolve()
    payload = {
        "schema_version": 1, "frozen_at": datetime.now(UTC).isoformat(),
        "config": config, "config_sha256": identity(config),
        "git_commit": git_commit(root), "source_sha256": source_digest(root),
        "git_status": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True
        ),
        "inputs": locate_inputs(root, config["instances"]),
        "checker": checker.relative_to(root).as_posix(), "checker_sha256": digest(checker),
        "environment": environment(), "matrix": matrix(config),
        "timing": "solver call includes setup and final oracle; parsing/checker separate",
        "memory": "fresh worker peak_wset on Windows; sampled RSS elsewhere; includes parsing",
        "raw_projection": "best-so-far changes and final weights; no full state/weight history",
    }
    output.mkdir(parents=True, exist_ok=True)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
    return payload


def run(output: Path, root: Path, *, selected_instances: list[str] | None = None) -> int:
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_hash = digest(manifest_path)
    if source_digest(root) != manifest["source_sha256"]:
        raise ValueError("source differs from frozen manifest; use a new experiment directory")
    if environment() != manifest["environment"]:
        raise ValueError("environment differs from frozen manifest")
    if digest(root / manifest["checker"]) != manifest["checker_sha256"]:
        raise ValueError("checker changed since freeze")
    for spec in manifest["inputs"].values():
        for field in ("model", "initial"):
            if digest(root / spec[field]) != spec[field + "_sha256"]:
                raise ValueError("input changed since freeze")
    config = manifest["config"]
    if selected_instances and not set(selected_instances) <= set(config["instances"]):
        raise ValueError("unknown instance filter")
    records = output / "records"
    records.mkdir(exist_ok=True)
    work = output / "work"
    work.mkdir(exist_ok=True)
    failures = 0
    for number, row in enumerate(manifest["matrix"], 1):
        if selected_instances and row["instance"] not in selected_instances:
            continue
        target = records / (row["id"] + ".json")
        if target.exists():
            previous = json.loads(target.read_text(encoding="utf-8"))
            signature = previous.pop("record_sha256")
            if signature != identity(previous) or previous["manifest_sha256"] != manifest_hash:
                raise ValueError(f"corrupt/mismatched completed record {target}")
            failures += previous["status"] != "ok"
            continue
        job = {**row, "input": manifest["inputs"][row["instance"]],
               "checker": manifest["checker"], "alns": config["alns"],
               "restricted": config["restricted"]}
        job_path = work / (row["id"] + ".job.json")
        result_path = work / (row["id"] + ".json")
        save(job_path, job)
        started = perf_counter()
        peak = 0
        timed_out = False
        env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                   MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
        error_path = work / (row["id"] + ".stderr.txt")
        with error_path.open("w", encoding="utf-8") as errors:
            process = subprocess.Popen(
                [sys.executable, "-m", "gmrp_alns.experiments.worker",
                 str(job_path.resolve()), str(result_path.resolve())],
                cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=errors,
            )
            monitor = psutil.Process(process.pid)
            while process.poll() is None:
                try:
                    memory = monitor.memory_info()
                    peak = max(peak, getattr(memory, "peak_wset", memory.rss))
                except psutil.NoSuchProcess:
                    pass
                try:
                    process.wait(timeout=0.02)
                except subprocess.TimeoutExpired:
                    if perf_counter() - started > row["budget"] + config["watchdog_grace_seconds"]:
                        timed_out = True
                        for child in monitor.children(recursive=True):
                            with suppress(psutil.NoSuchProcess):
                                child.kill()
                        process.kill()
                        process.wait()
            returncode = process.returncode
        payload: dict[str, Any]
        if timed_out:
            payload = {"status": "watchdog_timeout"}
        elif returncode != 0 or not result_path.exists():
            payload = {"status": "worker_failed", "returncode": returncode}
        else:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        payload.update(row)
        payload.update({
            "manifest_sha256": manifest_hash, "completed_at": datetime.now(UTC).isoformat(),
            "process_seconds": perf_counter() - started, "peak_memory_mb": peak / 2**20,
            "worker_stderr": error_path.read_text(encoding="utf-8"),
            "git_commit": manifest["git_commit"],
        })
        elapsed = payload.get("solver_seconds")
        payload["over_budget_seconds"] = max(0, elapsed - row["budget"]) if elapsed else None
        payload["within_budget_tolerance"] = (
            elapsed is not None and elapsed <= row["budget"] + config["budget_tolerance_seconds"]
        )
        solution = result_path.with_suffix(".sol")
        payload["solution_sha256"] = digest(solution) if solution.exists() else None
        payload["record_sha256"] = identity(payload)
        save(target, payload)
        failures += payload["status"] != "ok"
        print(f"{number}/{len(manifest['matrix'])} {row['instance']} {row['method']} "
              f"seed={row['seed']} {payload['status']}", flush=True)
    return 1 if failures else 0
