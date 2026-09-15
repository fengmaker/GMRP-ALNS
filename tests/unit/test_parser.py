from __future__ import annotations

from pathlib import Path

import pytest

from gmrp_alns.gmrp.model import Instance
from gmrp_alns.gmrp.parser import ParseError, parse_assignment, parse_instance, write_assignment


def test_parse_official_example(toy_instance: Instance) -> None:
    assert toy_instance.summary() == {
        "resources": 2,
        "machines": 4,
        "services": 2,
        "processes": 3,
        "neighborhoods": 2,
        "locations": 3,
        "balance_costs": 1,
        "dependencies": 1,
        "transient_resources": 1,
    }
    assert toy_instance.resources[0].transient
    assert toy_instance.services[1].dependencies == (0,)
    assert toy_instance.machines[2].move_costs == (4, 3, 0, 2)


def test_assignment_round_trip(
    tmp_path: Path, toy_instance: Instance, toy_solution: tuple[int, ...]
) -> None:
    destination = tmp_path / "solution.txt"
    write_assignment(destination, toy_solution)
    assert parse_assignment(destination, toy_instance) == toy_solution


@pytest.mark.parametrize("contents", ["0 1", "0 1 2 3", "0 1 99", "0 one 2"])
def test_reject_malformed_assignment(
    tmp_path: Path, toy_instance: Instance, contents: str
) -> None:
    path = tmp_path / "bad.txt"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ParseError):
        parse_assignment(path, toy_instance)


def test_reject_trailing_model_token(toy_dir: Path, tmp_path: Path) -> None:
    contents = (toy_dir / "model_toy.txt").read_text(encoding="utf-8")
    path = tmp_path / "bad_model.txt"
    path.write_text(contents + " 7", encoding="utf-8")
    with pytest.raises(ParseError, match="trailing"):
        parse_instance(path)

