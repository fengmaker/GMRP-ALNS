"""Acceptance criteria for metaheuristic search."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(slots=True)
class SimulatedAnnealing:
    """Geometrically cooled minimization acceptance with explicit reheating."""

    initial_temperature: float
    cooling_rate: float
    minimum_temperature: float = 1e-9
    temperature: float = 0.0

    def __post_init__(self) -> None:
        if self.initial_temperature <= 0:
            raise ValueError("initial_temperature must be positive")
        if not 0 < self.cooling_rate <= 1:
            raise ValueError("cooling_rate must be in (0, 1]")
        if self.minimum_temperature <= 0:
            raise ValueError("minimum_temperature must be positive")
        self.temperature = self.initial_temperature

    @classmethod
    def from_initial_cost(
        cls,
        initial_cost: int,
        *,
        target_acceptance_probability: float = 0.5,
        initial_worsening_fraction: float = 0.01,
        cooling_rate: float = 0.995,
        minimum_temperature: float = 1e-9,
    ) -> SimulatedAnnealing:
        """Fit a temperature that accepts a declared relative worsening initially."""

        if not 0 < target_acceptance_probability < 1:
            raise ValueError("target_acceptance_probability must be in (0, 1)")
        if initial_worsening_fraction <= 0:
            raise ValueError("initial_worsening_fraction must be positive")
        worsening = max(1.0, abs(initial_cost) * initial_worsening_fraction)
        temperature = -worsening / math.log(target_acceptance_probability)
        return cls(temperature, cooling_rate, minimum_temperature)

    def accept(self, current_cost: int, candidate_cost: int, rng: random.Random) -> bool:
        """Accept improvements deterministically and worsening moves probabilistically."""

        worsening = candidate_cost - current_cost
        if worsening <= 0:
            return True
        probability = math.exp(-worsening / self.temperature)
        return rng.random() < probability

    def cool(self) -> None:
        self.temperature = max(
            self.minimum_temperature,
            self.temperature * self.cooling_rate,
        )

    def reheat(self) -> None:
        self.temperature = self.initial_temperature
