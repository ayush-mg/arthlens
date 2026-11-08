"""Deterministic bootstrap summaries for per-task benchmark metric values."""

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BootstrapInterval:
    estimate: float
    lower: float
    upper: float
    confidence_level: float
    resamples: int


def bootstrap_mean_interval(
    values: Sequence[float],
    *,
    confidence_level: float = 0.95,
    resamples: int = 10_000,
    seed: int,
) -> BootstrapInterval:
    """Return a seeded percentile interval over resampled per-task means."""
    if not values:
        raise ValueError("values must contain at least one observation.")
    if (
        not isinstance(resamples, int)
        or isinstance(resamples, bool)
        or resamples < 1_000
    ):
        raise ValueError("resamples must be an integer of at least 1000.")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    if (
        isinstance(confidence_level, bool)
        or not math.isfinite(confidence_level)
        or not 0 < confidence_level < 1
    ):
        raise ValueError("confidence_level must be finite and between 0 and 1.")

    observations: list[float] = []
    for value in values:
        if isinstance(value, bool):
            raise TypeError("values must be finite numeric observations, not booleans.")
        try:
            observation = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("values must be finite numeric observations.") from exc
        if not math.isfinite(observation):
            raise ValueError("values must be finite numeric observations.")
        observations.append(observation)

    rng = random.Random(seed)
    count = len(observations)
    bootstrap_means = sorted(
        math.fsum(observations[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(resamples)
    )
    tail = (1 - confidence_level) / 2
    return BootstrapInterval(
        estimate=math.fsum(observations) / count,
        lower=_percentile(bootstrap_means, tail),
        upper=_percentile(bootstrap_means, 1 - tail),
        confidence_level=confidence_level,
        resamples=resamples,
    )


def _percentile(sorted_values: Sequence[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    fraction = position - lower_index
    return (
        sorted_values[lower_index] * (1 - fraction)
        + sorted_values[upper_index] * fraction
    )
