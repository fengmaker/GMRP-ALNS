"""Compare cached relocate evaluation with the full M1 correctness oracles."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from time import perf_counter

from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance
from gmrp_alns.gmrp.state import RelocateMove, SolutionState
from gmrp_alns.gmrp.validator import validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("initial", type=Path)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.samples <= 0:
        parser.error("--samples must be positive")

    instance = parse_instance(args.model)
    original = parse_assignment(args.initial, instance)
    state = SolutionState(instance, original, original)
    legal_moves = [
        state.make_relocate(process, destination)
        for process in range(instance.process_count)
        for destination in state.prefilter_machines(process)
        if state.can_relocate(process, destination)
    ]
    if not legal_moves:
        raise RuntimeError("the supplied assignment has no legal relocate moves")
    rng = random.Random(args.seed)
    moves = [rng.choice(legal_moves) for _ in range(args.samples)]

    incremental_started = perf_counter()
    incremental_deltas = []
    for move in moves:
        evaluation = state.evaluate_move(move)
        if not evaluation.feasible or evaluation.delta is None:
            raise AssertionError("a prevalidated relocate became infeasible")
        incremental_deltas.append(evaluation.delta.total_cost)
    incremental_seconds = perf_counter() - incremental_started

    full_started = perf_counter()
    full_deltas: list[int] = []
    for move in moves:
        candidate = list(original)
        candidate[move.process] = move.destination
        candidate_assignment = tuple(candidate)
        report = validate(instance, original, candidate_assignment)
        if not report.feasible:
            raise AssertionError("incremental feasibility disagrees with the full validator")
        objective = evaluate_objective(instance, original, candidate_assignment)
        full_deltas.append(objective.total_cost - state.total_cost)
    full_seconds = perf_counter() - full_started
    if incremental_deltas != full_deltas:
        mismatch = next(
            index
            for index, (incremental, full) in enumerate(
                zip(incremental_deltas, full_deltas, strict=True)
            )
            if incremental != full
        )
        move: RelocateMove = moves[mismatch]
        raise AssertionError(
            f"delta mismatch at sample {mismatch}, process {move.process}, "
            f"destination {move.destination}"
        )

    payload = {
        "model": str(args.model),
        "initial": str(args.initial),
        "dimensions": instance.summary(),
        "seed": args.seed,
        "samples": args.samples,
        "legal_relocates": len(legal_moves),
        "incremental_seconds": incremental_seconds,
        "full_seconds": full_seconds,
        "incremental_evaluations_per_second": args.samples / incremental_seconds,
        "full_evaluations_per_second": args.samples / full_seconds,
        "speedup": full_seconds / incremental_seconds,
        "delta_checksum": sum(incremental_deltas),
        "all_deltas_match": True,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
