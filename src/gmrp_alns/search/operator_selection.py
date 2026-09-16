"""Segmented roulette-wheel selection for adaptive ALNS operators."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(slots=True)
class _WeightState:
    weight: float
    score: float = 0.0
    uses: int = 0
    updates: int = 0


class AdaptiveOperatorPool:
    """Select named operators and update weights from per-segment rewards."""

    def __init__(
        self,
        names: tuple[str, ...],
        *,
        reaction_factor: float,
        initial_weight: float = 1.0,
        minimum_weight: float = 0.05,
    ) -> None:
        if not names or len(set(names)) != len(names):
            raise ValueError("operator names must be non-empty and unique")
        if not 0 < reaction_factor <= 1:
            raise ValueError("reaction_factor must be in (0, 1]")
        if initial_weight <= 0 or minimum_weight <= 0:
            raise ValueError("operator weights must be positive")
        self._names = names
        self._reaction_factor = reaction_factor
        self._minimum_weight = minimum_weight
        self._states = {
            name: _WeightState(initial_weight)
            for name in names
        }

    @property
    def names(self) -> tuple[str, ...]:
        return self._names

    def select(self, rng: random.Random) -> str:
        total = sum(self._states[name].weight for name in self._names)
        threshold = rng.random() * total
        cumulative = 0.0
        for name in self._names:
            cumulative += self._states[name].weight
            if threshold < cumulative:
                return name
        return self._names[-1]  # pragma: no cover - floating point guard

    def reward(self, name: str, score: float) -> None:
        if score < 0:
            raise ValueError("operator score must be non-negative")
        state = self._states[name]
        state.score += score
        state.uses += 1

    def update(self) -> None:
        for state in self._states.values():
            if state.uses:
                observed = state.score / state.uses
                state.weight = max(
                    self._minimum_weight,
                    (1 - self._reaction_factor) * state.weight
                    + self._reaction_factor * observed,
                )
                state.updates += 1
            state.score = 0.0
            state.uses = 0

    def weights(self) -> dict[str, float]:
        return {name: self._states[name].weight for name in self._names}

    def update_counts(self) -> dict[str, int]:
        return {name: self._states[name].updates for name in self._names}
