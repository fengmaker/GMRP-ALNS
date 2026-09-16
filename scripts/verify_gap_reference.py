"""Solve a downloaded OR-Library GAP file and compare official reference values."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from gmrp_alns.gap.exact import solve_exact
from gmrp_alns.gap.model import ObjectiveSense
from gmrp_alns.gap.parser import parse_orlib


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    project_root = args.manifest.resolve().parents[2]
    source = project_root / payload["file"]["path"]
    sense = cast(ObjectiveSense, payload["sense"])
    references = [int(value) for value in payload["reference_values"]]
    instances = parse_orlib(source, sense=sense, reference_values=references)
    records = []
    for instance in instances:
        result = solve_exact(
            instance,
            time_limit_seconds=args.time_limit,
            seed=args.seed,
        )
        records.append(
            {
                "instance": instance.name,
                "status": result.status,
                "objective": result.objective,
                "reference": instance.reference_optimum,
                "matches": result.optimal and result.objective == instance.reference_optimum,
                "wall_time_seconds": result.wall_time_seconds,
            }
        )
    output = {
        "manifest": str(args.manifest),
        "sense": sense,
        "seed": args.seed,
        "time_limit_seconds": args.time_limit,
        "all_match": all(record["matches"] for record in records),
        "instances": records,
    }
    print(json.dumps(output, indent=2))
    return 0 if output["all_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
