"""Strict parser for the multi-instance OR-Library GAP integer format."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from gmrp_alns.gap.model import GapInstance, ObjectiveSense


class GapParseError(ValueError):
    """Raised when an OR-Library GAP file is malformed."""


class _IntegerStream:
    def __init__(self, values: Iterable[int]) -> None:
        self.values = tuple(values)
        self.position = 0

    def take(self, label: str) -> int:
        if self.position >= len(self.values):
            raise GapParseError(f"unexpected end of file while reading {label}")
        value = self.values[self.position]
        self.position += 1
        return value

    def take_positive(self, label: str) -> int:
        value = self.take(label)
        if value <= 0:
            raise GapParseError(f"{label} must be positive, got {value}")
        return value

    def take_nonnegative(self, label: str) -> int:
        value = self.take(label)
        if value < 0:
            raise GapParseError(f"{label} must be non-negative, got {value}")
        return value

    def finish(self) -> None:
        remaining = len(self.values) - self.position
        if remaining:
            raise GapParseError(f"unexpected {remaining} trailing integer(s)")


def _read_integers(path: str | Path) -> tuple[int, ...]:
    source = Path(path)
    try:
        tokens = source.read_text(encoding="utf-8-sig").split()
    except OSError as exc:
        raise GapParseError(f"cannot read {source}: {exc}") from exc
    values: list[int] = []
    for index, token in enumerate(tokens):
        try:
            values.append(int(token))
        except ValueError as exc:
            raise GapParseError(f"token {index + 1} is not an integer: {token!r}") from exc
    return tuple(values)


def parse_orlib(
    path: str | Path,
    *,
    sense: ObjectiveSense,
    reference_values: Sequence[int] | None = None,
) -> tuple[GapInstance, ...]:
    """Parse every problem set in one OR-Library GAP file.

    OR-Library does not encode the objective direction or reference values in the data
    stream, so callers must supply the direction and may supply one reference value per set.
    """

    if sense not in ("minimize", "maximize"):
        raise GapParseError(f"unsupported objective sense: {sense!r}")
    source = Path(path)
    stream = _IntegerStream(_read_integers(source))
    problem_count = stream.take_positive("problem count")
    if reference_values is not None and len(reference_values) != problem_count:
        raise GapParseError(
            f"received {len(reference_values)} reference values for {problem_count} problems"
        )

    instances: list[GapInstance] = []
    for problem_id in range(problem_count):
        agents = stream.take_positive(f"problem[{problem_id}].agent_count")
        jobs = stream.take_positive(f"problem[{problem_id}].job_count")
        costs = tuple(
            tuple(stream.take(f"problem[{problem_id}].cost[{agent}][{job}]") for job in range(jobs))
            for agent in range(agents)
        )
        resources = tuple(
            tuple(
                stream.take_nonnegative(f"problem[{problem_id}].resource[{agent}][{job}]")
                for job in range(jobs)
            )
            for agent in range(agents)
        )
        capacities = tuple(
            stream.take_nonnegative(f"problem[{problem_id}].capacity[{agent}]")
            for agent in range(agents)
        )
        reference = None if reference_values is None else reference_values[problem_id]
        instances.append(
            GapInstance(
                costs=costs,
                resources=resources,
                capacities=capacities,
                sense=sense,
                name=f"{source.stem}-{problem_id + 1}",
                reference_optimum=reference,
            )
        )
    stream.finish()
    return tuple(instances)
