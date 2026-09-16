"""JSON command-line interface for the GMRP and classic GAP tracks."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from gmrp_alns.gap.exact import solve_exact
from gmrp_alns.gap.heuristics import cost_greedy, regret_greedy
from gmrp_alns.gap.parser import GapParseError, parse_orlib
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

    gap_command = subparsers.add_parser("gap", help="classic OR-Library GAP track")
    gap_subparsers = gap_command.add_subparsers(dest="gap_command", required=True)
    gap_parse = gap_subparsers.add_parser("parse", help="parse an OR-Library GAP file")
    gap_parse.add_argument("data", type=Path)
    gap_parse.add_argument("--sense", choices=("minimize", "maximize"), required=True)

    gap_solve = gap_subparsers.add_parser("solve", help="solve one GAP instance")
    gap_solve.add_argument("data", type=Path)
    gap_solve.add_argument("--sense", choices=("minimize", "maximize"), required=True)
    gap_solve.add_argument("--instance-index", type=int, default=1, help="one-based index")
    gap_solve.add_argument(
        "--algorithm",
        choices=("exact", "cost-greedy", "regret-greedy"),
        default="exact",
    )
    gap_solve.add_argument("--time-limit", type=float, default=60.0)
    gap_solve.add_argument("--seed", type=int, default=0)
    gap_solve.add_argument("--reference-value", type=int)
    return parser


def _run_gap(args: argparse.Namespace) -> int:
    instances = parse_orlib(args.data, sense=args.sense)
    if args.gap_command == "parse":
        _emit(
            {
                "file": str(args.data),
                "problem": "gap",
                "instance_count": len(instances),
                "instances": [instance.summary() for instance in instances],
            }
        )
        return 0

    if not 1 <= args.instance_index <= len(instances):
        raise ValueError(
            f"instance index {args.instance_index} is outside [1, {len(instances)}]"
        )
    instance = instances[args.instance_index - 1]
    if args.algorithm == "exact":
        result = solve_exact(
            instance,
            time_limit_seconds=args.time_limit,
            seed=args.seed,
        )
    elif args.algorithm == "cost-greedy":
        result = cost_greedy(
            instance,
            time_limit_seconds=args.time_limit,
            seed=args.seed,
        )
    else:
        result = regret_greedy(
            instance,
            time_limit_seconds=args.time_limit,
            seed=args.seed,
        )
    payload = result.as_dict(instance)
    payload["source"] = str(args.data)
    payload["instance_index"] = args.instance_index
    payload["reference_value"] = args.reference_value
    payload["matches_reference"] = (
        result.objective == args.reference_value if args.reference_value is not None else None
    )
    _emit(payload)
    return 0 if result.feasible else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "gap":
            return _run_gap(args)
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
    except (OSError, GapParseError, ParseError, ValueError) as exc:
        _emit({"error": str(exc)}, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
