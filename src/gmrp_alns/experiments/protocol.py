"""Experiment identity, input hashes, and deterministic run matrix."""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import subprocess
from pathlib import Path
from typing import Any

METHODS = {
    "initial", "relocate", "vnd", "random-lns", "alns", "restricted",
    "random-only", "no-restart", "greedy-only",
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identity(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def git_commit(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def source_digest(root: Path) -> str:
    paths = sorted((root / "src").rglob("*.py"))
    return identity({p.relative_to(root).as_posix(): digest(p) for p in paths})


def load_config(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    for key in ("instances", "seeds", "time_limits", "methods"):
        values = config[key]
        if not values or len(values) != len(set(values)):
            raise ValueError(f"{key} must be non-empty and unique")
    if any(not re.fullmatch(r"[a-z0-9_]+", name) for name in config["instances"]):
        raise ValueError("invalid instance name")
    if any(type(seed) is not int or seed < 0 for seed in config["seeds"]):
        raise ValueError("seeds must be non-negative integers")
    if any(not math.isfinite(t) or t <= 0 for t in config["time_limits"]):
        raise ValueError("time limits must be finite and positive")
    if not set(config["methods"]) <= METHODS:
        raise ValueError("unknown method")
    if not set(config.get("ablation_instances", [])) <= set(config["instances"]):
        raise ValueError("ablation instances must belong to the main matrix")
    if not set(config.get("ablation_methods", [])) <= METHODS:
        raise ValueError("unknown ablation method")
    return config


def matrix(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name in config["instances"]:
        methods = list(config["methods"])
        if name in config.get("ablation_instances", []):
            methods += config.get("ablation_methods", [])
        for budget in config["time_limits"]:
            for seed in config["seeds"]:
                for method in dict.fromkeys(methods):
                    row = dict(instance=name, method=method, seed=seed, budget=budget)
                    row["id"] = identity(row)[:20]
                    rows.append(row)
    random.Random(config["order_seed"]).shuffle(rows)
    return rows


def locate_inputs(root: Path, names: list[str]) -> dict[str, Any]:
    result = {}
    for name in names:
        matches = list((root / "data").rglob(f"model_{name}.txt"))
        if len(matches) != 1:
            raise ValueError(f"expected one model for {name}, got {len(matches)}")
        model = matches[0]
        initial = model.with_name(f"assignment_{name}.txt")
        result[name] = {
            "model": model.relative_to(root).as_posix(),
            "initial": initial.relative_to(root).as_posix(),
            "model_sha256": digest(model),
            "initial_sha256": digest(initial),
        }
    return result
