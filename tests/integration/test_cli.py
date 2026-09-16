from __future__ import annotations

import json
from pathlib import Path

from gmrp_alns.cli import main


def test_parse_command(toy_dir: Path, capsys: object) -> None:
    assert main(["parse", str(toy_dir / "model_toy.txt")]) == 0
    output = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert output["processes"] == 3


def test_validate_and_score_commands(toy_dir: Path, capsys: object) -> None:
    common = [
        str(toy_dir / "model_toy.txt"),
        str(toy_dir / "assignment_toy.txt"),
        str(toy_dir / "solution_toy.txt"),
    ]
    assert main(["validate", *common]) == 0
    assert json.loads(capsys.readouterr().out)["feasible"]  # type: ignore[attr-defined]
    assert main(["score", *common]) == 0
    score = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert score["objective"]["total_cost"] == 2411


def test_validate_infeasible_returns_one(toy_dir: Path, tmp_path: Path, capsys: object) -> None:
    candidate = tmp_path / "bad.sol"
    candidate.write_text("0 0 0\n", encoding="utf-8")
    exit_code = main(
        [
            "validate",
            str(toy_dir / "model_toy.txt"),
            str(toy_dir / "assignment_toy.txt"),
            str(candidate),
        ]
    )
    assert exit_code == 1
    assert not json.loads(capsys.readouterr().out)["feasible"]  # type: ignore[attr-defined]


def test_gap_parse_and_solve_commands(toy_dir: Path, capsys: object) -> None:
    data = str(toy_dir / "gap_toy.txt")
    assert main(["gap", "parse", data, "--sense", "minimize"]) == 0
    parsed = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert parsed["instances"][0]["jobs"] == 4

    assert (
        main(
            [
                "gap",
                "solve",
                data,
                "--sense",
                "minimize",
                "--algorithm",
                "exact",
                "--seed",
                "42",
                "--reference-value",
                "8",
            ]
        )
        == 0
    )
    solved = json.loads(capsys.readouterr().out)  # type: ignore[attr-defined]
    assert solved["feasible"]
    assert solved["optimal"]
    assert solved["matches_reference"]
