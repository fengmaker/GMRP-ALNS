from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from gmrp_alns.experiments.protocol import digest, identity, load_config, matrix
from gmrp_alns.experiments.report import load_records, paired, summarize
from gmrp_alns.experiments.runner import save
from gmrp_alns.experiments.worker import execute
from gmrp_alns.gmrp.checker import CheckerResult


def test_frozen_matrix_has_unique_seeded_order() -> None:
    config = load_config(Path("configs/m7_benchmark.json"))
    first = matrix(config)
    assert first == matrix(config)
    assert len(first) == len({r["id"] for r in first}) == 660
    assert len([r for r in first if r["method"] == "alns"]) == 100


def _row(method: str, seed: int, cost: int, **changes: Any) -> dict[str, Any]:
    row = dict(instance="toy", method=method, budget=1.0, seed=seed,
               status="ok", official_valid=True, best_cost=cost, initial_cost=100,
               solver_seconds=1.05, within_budget_tolerance=True,
               time_to_best_seconds=0.5, peak_memory_mb=20)
    row.update(changes)
    return row


def test_aggregation_retains_failures_and_uses_sample_sd() -> None:
    rows = [_row("alns", 1, 80), _row("alns", 2, 60),
            _row("alns", 3, 100, status="error"),
            _row("alns", 4, 100, status="missing")]
    result = summarize(rows)[0]
    assert result["mean_cost"] == 70
    assert result["sd_cost"] == pytest.approx(14.14213562)
    assert result["feasible_rate"] == 0.5
    assert result["failures"] == result["missing"] == 1
    assert result["mean_improvement_percent"] == 30


def test_pairing_matches_seed_and_exposes_overruns() -> None:
    rows = [_row("alns", 1, 80), _row("restricted", 2, 60),
            _row("restricted", 1, 70, within_budget_tolerance=False),
            _row("alns", 2, 50), _row("alns", 3, 90)]
    result = paired(rows, "alns", "restricted", ["toy"])
    assert (result["wins"], result["losses"], result["unavailable_pairs"]) == (1, 1, 1)
    assert result["paired_mean_gain_percentage_points"] == 0
    assert result["both_within_budget_pairs"] == 1
    assert result["timely_mean_gain_percentage_points"] == -10


def test_records_detect_tampering_and_materialize_missing(tmp_path: Path) -> None:
    planned = [dict(id="a", instance="toy", method="alns", budget=1.0, seed=1),
               dict(id="b", instance="toy", method="alns", budget=1.0, seed=2)]
    save(tmp_path / "manifest.json", {"matrix": planned})
    records = tmp_path / "records"
    records.mkdir()
    record = {**planned[0], "status": "error",
              "manifest_sha256": digest(tmp_path / "manifest.json")}
    record["record_sha256"] = identity(record)
    save(records / "a.json", record)
    _, rows = load_records(tmp_path)
    assert [r["status"] for r in rows] == ["error", "missing"]
    record["status"] = "ok"
    save(records / "a.json", record)
    with pytest.raises(ValueError, match="corrupt"):
        load_records(tmp_path)


def test_worker_checks_cost_and_records_end_to_end_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("gmrp_alns.experiments.worker.run_official_checker",
                        lambda *args, **kwargs: CheckerResult(
                            0, "Solution is valid\nTotal objective cost is 2411", ""))
    job = dict(input={"model": "data/toy/model_toy.txt",
                      "initial": "data/toy/assignment_toy.txt"},
               method="alns", budget=1.0, seed=42, instance="toy", checker="dummy",
               alns={"max_iterations": 2}, restricted={})
    result = execute(job, Path.cwd(), tmp_path / "candidate.sol")
    assert result["status"] == "ok"
    assert result["best_cost"] == 2411
    assert result["solver_seconds"] >= result["wall_time_seconds"]
    assert result["worker_peak_memory_mb"] > 0
    assert "assignment" not in result
    assert (tmp_path / "candidate.sol").exists()
    json.dumps(result)
