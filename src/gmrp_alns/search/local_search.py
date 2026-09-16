"""Strict-feasible relocate local search and relocate/swap VND."""

from __future__ import annotations

import random
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.state import Move, ObjectiveDelta, RelocateMove, SolutionState
from gmrp_alns.search.common import build_result
from gmrp_alns.search.model import OperatorStats, SearchResult, TracePoint

ImprovementStrategy = Literal["first", "best"]


@dataclass(slots=True)
class _Stats:
    calls: int = 0
    successes: int = 0
    candidate_evaluations: int = 0
    total_improvement: int = 0
    wall_time_seconds: float = 0.0

    def freeze(self) -> OperatorStats:
        return OperatorStats(
            calls=self.calls,
            successes=self.successes,
            candidate_evaluations=self.candidate_evaluations,
            total_improvement=self.total_improvement,
            wall_time_seconds=self.wall_time_seconds,
        )


@dataclass(frozen=True, slots=True)
class _SelectedMove:
    move: Move
    delta: ObjectiveDelta


def _validate_parameters(
    *,
    strategy: ImprovementStrategy,
    time_limit_seconds: float,
    max_iterations: int | None,
    top_k: int,
    max_swap_candidates: int,
) -> None:
    if strategy not in ("first", "best"):
        raise ValueError(f"unknown improvement strategy: {strategy}")
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive")
    if max_iterations is not None and max_iterations < 0:
        raise ValueError("max_iterations must be non-negative")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if max_swap_candidates <= 0:
        raise ValueError("max_swap_candidates must be positive")


def _find_relocate(
    state: SolutionState,
    *,
    strategy: ImprovementStrategy,
    rng: random.Random,
    top_k: int,
    deadline: float,
) -> tuple[_SelectedMove | None, int]:
    processes = list(range(state.instance.process_count))
    rng.shuffle(processes)
    best: _SelectedMove | None = None
    evaluations = 0
    for process in processes:
        ranked: list[_SelectedMove] = []
        for destination in state.prefilter_machines(process):
            if perf_counter() >= deadline:
                return best, evaluations
            move = state.make_relocate(process, destination)
            evaluation = state.evaluate_move(move)
            evaluations += 1
            if not evaluation.feasible or evaluation.delta is None:
                continue
            ranked.append(_SelectedMove(move, evaluation.delta))
        ranked.sort(key=lambda selected: selected.delta.total_cost)
        for selected in ranked[:top_k]:
            if selected.delta.total_cost >= 0:
                break
            if strategy == "first":
                return selected, evaluations
            if best is None or selected.delta.total_cost < best.delta.total_cost:
                best = selected
    return best, evaluations


def _sample_swap_pairs(
    process_count: int, *, rng: random.Random, limit: int
) -> list[tuple[int, int]]:
    total = process_count * (process_count - 1) // 2
    if total <= limit:
        pairs = [
            (first, second)
            for first in range(process_count)
            for second in range(first + 1, process_count)
        ]
        rng.shuffle(pairs)
        return pairs

    pairs = []
    seen: set[tuple[int, int]] = set()
    while len(pairs) < limit:
        first = rng.randrange(process_count)
        second = rng.randrange(process_count - 1)
        if second >= first:
            second += 1
        pair = (first, second) if first < second else (second, first)
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append(pair)
    return pairs


def _find_swap(
    state: SolutionState,
    *,
    strategy: ImprovementStrategy,
    rng: random.Random,
    max_candidates: int,
    deadline: float,
) -> tuple[_SelectedMove | None, int]:
    best: _SelectedMove | None = None
    evaluations = 0
    pairs = _sample_swap_pairs(
        state.instance.process_count,
        rng=rng,
        limit=max_candidates,
    )
    for first, second in pairs:
        if perf_counter() >= deadline:
            return best, evaluations
        if state.machine_of_process[first] == state.machine_of_process[second]:
            continue
        move = state.make_swap(first, second)
        evaluation = state.evaluate_move(move)
        evaluations += 1
        if (
            not evaluation.feasible
            or evaluation.delta is None
            or evaluation.delta.total_cost >= 0
        ):
            continue
        selected = _SelectedMove(move, evaluation.delta)
        if strategy == "first":
            return selected, evaluations
        if best is None or selected.delta.total_cost < best.delta.total_cost:
            best = selected
    return best, evaluations


def _run_search(
    instance: Instance,
    original: Assignment,
    assignment: Assignment,
    *,
    algorithm: str,
    strategy: ImprovementStrategy,
    use_swap: bool,
    time_limit_seconds: float,
    seed: int,
    max_iterations: int | None,
    top_k: int,
    max_swap_candidates: int,
) -> SearchResult:
    _validate_parameters(
        strategy=strategy,
        time_limit_seconds=time_limit_seconds,
        max_iterations=max_iterations,
        top_k=top_k,
        max_swap_candidates=max_swap_candidates,
    )
    started = perf_counter()
    deadline = started + time_limit_seconds
    state = SolutionState(instance, original, assignment)
    initial_cost = evaluate_objective(instance, original, assignment).total_cost
    rng = random.Random(seed)
    trace = [TracePoint(0.0, 0, initial_cost, initial_cost, "initial")]
    time_to_best = 0.0
    iterations = 0
    evaluations = 0
    relocate_stats = _Stats()
    swap_stats = _Stats()
    neighborhood = "relocate"

    while perf_counter() < deadline and (
        max_iterations is None or iterations < max_iterations
    ):
        if neighborhood == "relocate":
            operator_started = perf_counter()
            selected, checked = _find_relocate(
                state,
                strategy=strategy,
                rng=rng,
                top_k=top_k,
                deadline=deadline,
            )
            relocate_stats.calls += 1
            relocate_stats.candidate_evaluations += checked
            relocate_stats.wall_time_seconds += perf_counter() - operator_started
        else:
            operator_started = perf_counter()
            selected, checked = _find_swap(
                state,
                strategy=strategy,
                rng=rng,
                max_candidates=max_swap_candidates,
                deadline=deadline,
            )
            swap_stats.calls += 1
            swap_stats.candidate_evaluations += checked
            swap_stats.wall_time_seconds += perf_counter() - operator_started
        evaluations += checked

        if selected is None:
            if use_swap and neighborhood == "relocate" and perf_counter() < deadline:
                neighborhood = "swap"
                continue
            break

        previous = state.total_cost
        applied = state.apply_move(selected.move)
        if applied != selected.delta:  # pragma: no cover - invariant guard
            raise AssertionError("move delta changed between evaluation and apply")
        improvement = previous - state.total_cost
        if improvement <= 0:  # pragma: no cover - selection guard
            raise AssertionError("local search accepted a non-improving move")
        iterations += 1
        elapsed = perf_counter() - started
        time_to_best = elapsed
        trace.append(
            TracePoint(elapsed, iterations, state.total_cost, state.total_cost, neighborhood)
        )
        selected_stats = (
            relocate_stats if isinstance(selected.move, RelocateMove) else swap_stats
        )
        selected_stats.successes += 1
        selected_stats.total_improvement += improvement
        neighborhood = "relocate"

    wall_time = perf_counter() - started
    frozen_stats = {"relocate": relocate_stats.freeze()}
    if use_swap:
        frozen_stats["swap"] = swap_stats.freeze()
    return build_result(
        algorithm=algorithm,
        state=state,
        initial=original,
        initial_cost=initial_cost,
        seed=seed,
        time_limit_seconds=time_limit_seconds,
        wall_time_seconds=wall_time,
        time_to_best_seconds=time_to_best,
        iterations=iterations,
        candidate_evaluations=evaluations,
        trace=trace,
        operator_stats=frozen_stats,
        config={
            "strategy": strategy,
            "top_k": top_k,
            "max_swap_candidates": max_swap_candidates if use_swap else 0,
            "max_iterations": max_iterations,
        },
    )


def relocate_search(
    instance: Instance,
    original: Assignment,
    assignment: Assignment,
    *,
    strategy: ImprovementStrategy = "first",
    time_limit_seconds: float = 60.0,
    seed: int = 0,
    max_iterations: int | None = None,
    top_k: int = 20,
) -> SearchResult:
    """Run strict-feasible relocate first- or best-improvement search."""

    return _run_search(
        instance,
        original,
        assignment,
        algorithm=f"relocate-{strategy}",
        strategy=strategy,
        use_swap=False,
        time_limit_seconds=time_limit_seconds,
        seed=seed,
        max_iterations=max_iterations,
        top_k=top_k,
        max_swap_candidates=1,
    )


def vnd_search(
    instance: Instance,
    original: Assignment,
    assignment: Assignment,
    *,
    strategy: ImprovementStrategy = "first",
    time_limit_seconds: float = 60.0,
    seed: int = 0,
    max_iterations: int | None = None,
    top_k: int = 20,
    max_swap_candidates: int = 5_000,
) -> SearchResult:
    """Run relocate/swap variable-neighborhood descent."""

    return _run_search(
        instance,
        original,
        assignment,
        algorithm=f"vnd-{strategy}",
        strategy=strategy,
        use_swap=True,
        time_limit_seconds=time_limit_seconds,
        seed=seed,
        max_iterations=max_iterations,
        top_k=top_k,
        max_swap_candidates=max_swap_candidates,
    )
