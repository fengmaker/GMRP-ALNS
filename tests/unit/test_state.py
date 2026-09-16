from __future__ import annotations

import random

import pytest

from gmrp_alns.gmrp.model import (
    Assignment,
    Instance,
    Machine,
    Process,
    Resource,
    Service,
)
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.state import InfeasibleMoveError, Move, RelocateMove, SolutionState
from gmrp_alns.gmrp.validator import validate


def _swap_instance() -> tuple[Instance, Assignment]:
    instance = Instance(
        resources=(Resource(transient=False, load_cost_weight=3),),
        machines=(
            Machine(
                neighborhood=0,
                location=0,
                capacities=(10,),
                safety_capacities=(5,),
                move_costs=(0, 4),
            ),
            Machine(
                neighborhood=0,
                location=1,
                capacities=(10,),
                safety_capacities=(5,),
                move_costs=(2, 0),
            ),
        ),
        services=(
            Service(spread_min=1, dependencies=()),
            Service(spread_min=1, dependencies=()),
        ),
        processes=(
            Process(service=0, requirements=(7,), move_cost=2),
            Process(service=1, requirements=(1,), move_cost=3),
        ),
        balance_costs=(),
        process_move_cost_weight=5,
        service_move_cost_weight=7,
        machine_move_cost_weight=11,
    )
    return instance, (0, 1)


def _assert_incremental_matches_full(
    state: SolutionState, move: Move
) -> None:
    before = state.snapshot()
    evaluation = state.evaluate_move(move)
    assert evaluation.feasible
    assert evaluation.delta is not None
    candidate = list(state.assignment)
    if isinstance(move, RelocateMove):
        candidate[move.process] = move.destination
    else:
        candidate[move.first_process] = move.second_machine
        candidate[move.second_process] = move.first_machine
    full_before = state.total_cost
    full_after = evaluate_objective(state.instance, state.original, tuple(candidate)).total_cost
    assert evaluation.delta.total_cost == full_after - full_before

    applied_delta = state.apply_move(move)
    assert applied_delta == evaluation.delta
    assert state.assignment == tuple(candidate)
    assert state.total_cost == full_after
    assert validate(state.instance, state.original, state.assignment).feasible
    state.assert_consistent()

    undo_delta = state.undo_move(move)
    assert undo_delta.total_cost == -evaluation.delta.total_cost
    assert state.snapshot() == before


def test_relocate_delta_apply_undo_and_candidates(
    toy_instance: Instance, toy_original: Assignment
) -> None:
    state = SolutionState(toy_instance, toy_original, toy_original)
    assert state.prefilter_machines(1) == (1, 2)
    assert state.candidate_machines(1, top_k=1) == (2,)
    move = state.make_relocate(1, 2)
    _assert_incremental_matches_full(state, move)
    assert not state.can_relocate(0, 1)
    with pytest.raises(InfeasibleMoveError, match="transient"):
        state.relocate_delta(0, 1)


def test_swap_delta_apply_undo() -> None:
    instance, original = _swap_instance()
    state = SolutionState(instance, original, original)
    assert state.can_swap(0, 1)
    _assert_incremental_matches_full(state, state.make_swap(0, 1))


def test_ten_thousand_random_legal_moves_match_full_oracle(
    toy_instance: Instance, toy_original: Assignment
) -> None:
    rng = random.Random(42)
    toy_state = SolutionState(toy_instance, toy_original, toy_original)
    swap_instance, swap_original = _swap_instance()
    swap_state = SolutionState(swap_instance, swap_original, swap_original)

    for index in range(10_000):
        state = swap_state if index % 10 == 0 else toy_state
        moves: list[Move] = []
        for process in range(state.instance.process_count):
            for destination in range(state.instance.machine_count):
                if destination == state.machine_of_process[process]:
                    continue
                move = state.make_relocate(process, destination)
                if state.is_move_feasible(move):
                    moves.append(move)
        for first in range(state.instance.process_count):
            for second in range(first + 1, state.instance.process_count):
                move = state.make_swap(first, second)
                if state.is_move_feasible(move):
                    moves.append(move)
        assert moves
        _assert_incremental_matches_full(state, rng.choice(moves))
