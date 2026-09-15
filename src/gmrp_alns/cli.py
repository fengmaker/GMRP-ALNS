"""Small JSON command-line interface for the M1 foundation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.parser import ParseError, parse_assignment, parse_instance
from gmrp_alns.gmrp.validator import validate


def _emit(payload: dict[str, Any], *, stream: Any | None = None) -> None:
    if stream is None:
        stream = sys.stdout
    json.dump(payload, stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def _add_assignment_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("model", type=Path, help="official model file")
    parser.add_argument("initial", type=Path, help="official original assignment file")
    parser.add_argument("solution", type=Path, help="assignment to evaluate")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gmrp-alns")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_command = subparsers.add_parser("parse", help="parse a model and print dimensions")
    parse_command.add_argument("model", type=Path)

    validate_command = subparsers.add_parser("validate", help="check all hard constraints")
    _add_assignment_arguments(validate_command)

    score_command = subparsers.add_parser("score", help="compute official objective components")
    _add_assignment_arguments(score_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        instance = parse_instance(args.model)
        if args.command == "parse":
            _emit({"model": str(args.model), **instance.summary()})
            return 0

        original = parse_assignment(args.initial, instance)
        solution = parse_assignment(args.solution, instance)
        report = validate(instance, original, solution)
        if args.command == "validate":
            _emit(report.as_dict())
            return 0 if report.feasible else 1

        objective = evaluate_objective(instance, original, solution)
        _emit({**report.as_dict(), "objective": objective.as_dict()})
        return 0 if report.feasible else 1
    except (OSError, ParseError, ValueError) as exc:
        _emit({"error": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
