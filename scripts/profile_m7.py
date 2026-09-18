"""Separate instrumented profile; never mix profiled costs into benchmark rows."""

from __future__ import annotations

import argparse
import cProfile
import json
import pstats
from pathlib import Path

from gmrp_alns.experiments.protocol import digest, git_commit
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance
from gmrp_alns.search.alns import adaptive_alns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("initial", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--time-limit", type=float, default=1)
    args = parser.parse_args()
    instance = parse_instance(args.model)
    original = parse_assignment(args.initial, instance)
    profiler = cProfile.Profile()
    profiler.enable()
    result = adaptive_alns(instance, original, original, seed=42,
                           time_limit_seconds=args.time_limit)
    profiler.disable()
    stats = pstats.Stats(profiler)
    rows = []
    root = Path.cwd()
    for (filename, line, function), (primitive, calls, own, cumulative, _) in stats.stats.items():
        if str(root / "src") not in filename:
            continue
        rows.append({"file": Path(filename).relative_to(root).as_posix(), "line": line,
                     "function": function, "primitive_calls": primitive, "calls": calls,
                     "self_seconds": own, "cumulative_seconds": cumulative})
    rows.sort(key=lambda row: row["cumulative_seconds"], reverse=True)
    payload = {"git_commit": git_commit(root), "model_sha256": digest(args.model),
               "initial_sha256": digest(args.initial), "seed": 42,
               "requested_seconds": args.time_limit,
               "instrumented_solver_seconds": result.wall_time_seconds,
               "note": "cProfile overhead changes iteration count; costs excluded from benchmark",
               "functions": rows[:30]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
