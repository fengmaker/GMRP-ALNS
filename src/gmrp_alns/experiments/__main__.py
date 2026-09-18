"""Run with python -m gmrp_alns.experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from gmrp_alns.experiments.runner import freeze, run


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    freezing = commands.add_parser("freeze")
    freezing.add_argument("config", type=Path)
    freezing.add_argument("output", type=Path)
    freezing.add_argument("--checker", type=Path, required=True)
    running = commands.add_parser("run")
    running.add_argument("output", type=Path)
    running.add_argument("--instances", nargs="+")
    reporting = commands.add_parser("report")
    reporting.add_argument("input", type=Path)
    reporting.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    if args.command == "freeze":
        manifest = freeze(args.config, args.output, root, args.checker)
        print(f"Frozen {len(manifest['matrix'])} runs in {args.output}")
    elif args.command == "run":
        return run(args.output, root, selected_instances=args.instances)
    else:
        from gmrp_alns.experiments.report import report

        report(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
