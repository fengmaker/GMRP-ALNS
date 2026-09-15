from __future__ import annotations

from pathlib import Path

import pytest

from gmrp_alns.gmrp.model import Assignment, Instance
from gmrp_alns.gmrp.parser import parse_assignment, parse_instance


@pytest.fixture(scope="session")
def toy_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "toy"


@pytest.fixture(scope="session")
def toy_instance(toy_dir: Path) -> Instance:
    return parse_instance(toy_dir / "model_toy.txt")


@pytest.fixture(scope="session")
def toy_original(toy_dir: Path, toy_instance: Instance) -> Assignment:
    return parse_assignment(toy_dir / "assignment_toy.txt", toy_instance)


@pytest.fixture(scope="session")
def toy_solution(toy_dir: Path, toy_instance: Instance) -> Assignment:
    return parse_assignment(toy_dir / "solution_toy.txt", toy_instance)

