from __future__ import annotations

from itertools import combinations, product
from time import perf_counter

from gmrp_alns.exact.restricted_repair import restricted_cpsat_repair
from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.objective import evaluate_objective
from gmrp_alns.gmrp.validator import validate
from gmrp_alns.search.alns import adaptive_alns


def test_restricted_cpsat_finds_verified_toy_improvement(
    toy_instance: Instance,
    toy_original: Assignment,
    toy_solution: Assignment,
) -> None:
    outcome = restricted_cpsat_repair(
        toy_instance,
        toy_original,
        toy_original,
        tuple(range(toy_instance.process_count)),
        deadline=perf_counter() + 2,
        time_limit_seconds=1,
        candidate_machine_limit=toy_instance.machine_count,
        variable_limit=20,
        seed=42,
    )
    assert outcome.status == "optimal"
    assert outcome.assignment == toy_solution
    assert outcome.objective == evaluate_objective(
        toy_instance, toy_original, toy_solution
    )
    assert outcome.assignment_variables <= 20
    assert outcome.solver_time_limit_seconds <= 1
    assert validate(toy_instance, toy_original, outcome.assignment).feasible


def test_restricted_cpsat_matches_bruteforce_on_every_toy_neighborhood(
    toy_instance: Instance,
    toy_original: Assignment,
) -> None:
    process_ids = range(toy_instance.process_count)
    for size in range(1, toy_instance.process_count + 1):
        for removed in combinations(process_ids, size):
            feasible: list[tuple[int, Assignment]] = []
            for destinations in product(range(toy_instance.machine_count), repeat=size):
                candidate = list(toy_original)
                for process_id, destination in zip(removed, destinations, strict=True):
                    candidate[process_id] = destination
                assignment = tuple(candidate)
                if validate(toy_instance, toy_original, assignment).feasible:
                    feasible.append(
                        (
                            evaluate_objective(
                                toy_instance, toy_original, assignment
                            ).total_cost,
                            assignment,
                        )
                    )
            best_cost = min(cost for cost, _ in feasible)
            outcome = restricted_cpsat_repair(
                toy_instance,
                toy_original,
                toy_original,
                removed,
                deadline=perf_counter() + 2,
                time_limit_seconds=1,
                candidate_machine_limit=toy_instance.machine_count,
                variable_limit=20,
                seed=42,
            )
            initial_cost = evaluate_objective(
                toy_instance, toy_original, toy_original
            ).total_cost
            if best_cost < initial_cost:
                assert outcome.objective is not None
                assert outcome.objective.total_cost == best_cost
            else:
                assert outcome.assignment is None
                assert outcome.objective is None


def test_restricted_cpsat_failure_keeps_incumbent_untouched(
    toy_instance: Instance,
    toy_original: Assignment,
) -> None:
    outcome = restricted_cpsat_repair(
        toy_instance,
        toy_original,
        toy_original,
        (0, 1),
        deadline=perf_counter() + 2,
        variable_limit=1,
    )
    assert outcome.status == "variable_limit"
    assert outcome.assignment is None
    assert outcome.objective is None
    assert validate(toy_instance, toy_original, toy_original).feasible


def test_restricted_cpsat_respects_expired_deadline(
    toy_instance: Instance,
    toy_original: Assignment,
) -> None:
    outcome = restricted_cpsat_repair(
        toy_instance,
        toy_original,
        toy_original,
        (0,),
        deadline=perf_counter() - 1,
    )
    assert outcome.status == "deadline_before_build"
    assert outcome.assignment is None
    assert outcome.solver_time_limit_seconds == 0


def test_adaptive_alns_records_restricted_repair_calls(
    toy_instance: Instance,
    toy_original: Assignment,
    toy_solution: Assignment,
) -> None:
    result = adaptive_alns(
        toy_instance,
        toy_original,
        toy_original,
        time_limit_seconds=2,
        seed=42,
        max_iterations=1,
        destroy_size=toy_instance.process_count,
        warm_start_fraction=0,
        restricted_repair_interval=1,
        restricted_repair_time_limit_seconds=1,
        restricted_repair_candidate_machines=toy_instance.machine_count,
        restricted_repair_variable_limit=20,
    )
    assert result.algorithm == "adaptive-alns-restricted"
    assert result.assignment == toy_solution
    stats = result.operator_stats["repair:restricted-cpsat"]
    assert stats.calls == stats.successes == stats.new_best == 1
    calls = result.config["restricted_repair"]["calls"]
    assert len(calls) == 1
    assert calls[0]["status"] == "optimal"
    assert calls[0]["assignment_variables"] <= 20
