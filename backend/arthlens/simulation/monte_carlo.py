"""Reproducible Monte Carlo summaries for explicitly supplied stochastic models."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite, sqrt
from types import MappingProxyType

import numpy as np
from numpy.random import PCG64, Generator

from backend.arthlens.domain.simulation import SimulationMetadata


@dataclass(frozen=True)
class SimulationOutcome:
    metrics: Mapping[str, float]
    cash_shortfall: bool

    def __post_init__(self) -> None:
        metrics = _validated_metrics(self.metrics)
        if not isinstance(self.cash_shortfall, bool):
            raise ValueError("cash_shortfall must be a bool.")
        object.__setattr__(self, "metrics", MappingProxyType(metrics))


@dataclass(frozen=True)
class MetricSummary:
    mean: float
    quantiles: Mapping[float, float]
    standard_error: float
    converged: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantiles", MappingProxyType(dict(self.quantiles)))


@dataclass(frozen=True)
class MonteCarloResult:
    metadata: SimulationMetadata
    metrics: Mapping[str, MetricSummary]
    shortfall_probability: float
    shortfall_probability_standard_error: float
    shortfall_probability_converged: bool

    @property
    def converged(self) -> bool:
        return self.shortfall_probability_converged and all(
            summary.converged for summary in self.metrics.values()
        )

    def __post_init__(self) -> None:
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))


def run_monte_carlo(
    sample: Callable[[Generator], SimulationOutcome],
    *,
    metadata: SimulationMetadata,
    quantile_levels: Sequence[float],
    minimum_sample_count: int,
    convergence_tolerances: Mapping[str, float],
    shortfall_probability_tolerance: float,
) -> MonteCarloResult:
    """Run a fixed-size PCG64 simulation and report explicit convergence criteria."""
    if not callable(sample):
        raise TypeError("sample must be callable.")
    if not isinstance(metadata, SimulationMetadata):
        raise TypeError("metadata must be a SimulationMetadata instance.")
    if (
        isinstance(minimum_sample_count, bool)
        or not isinstance(minimum_sample_count, int)
        or not 2 <= minimum_sample_count <= metadata.sample_count
    ):
        raise ValueError("minimum_sample_count must be between 2 and sample_count.")

    levels = _quantile_levels(quantile_levels)
    if not isinstance(convergence_tolerances, Mapping) or not convergence_tolerances:
        raise ValueError("convergence_tolerances must be a non-empty metric-to-tolerance mapping.")
    tolerances = {
        _metric_name(name): _nonnegative_finite(tolerance, f"tolerance for {name}")
        for name, tolerance in convergence_tolerances.items()
    }
    shortfall_tolerance = _nonnegative_finite(
        shortfall_probability_tolerance,
        "shortfall_probability_tolerance",
    )

    rng = Generator(PCG64(metadata.seed))
    metric_samples: dict[str, list[float]] | None = None
    shortfall_count = 0
    for sample_index in range(metadata.sample_count):
        outcome = sample(rng)
        if not isinstance(outcome, SimulationOutcome):
            raise TypeError(f"sample {sample_index} must return SimulationOutcome.")
        if metric_samples is None:
            if set(outcome.metrics) != set(tolerances):
                raise ValueError("convergence_tolerances must name every sampled metric exactly.")
            metric_samples = {name: [] for name in outcome.metrics}
        elif set(outcome.metrics) != set(metric_samples):
            raise ValueError(f"sample {sample_index} returned a different set of metrics.")
        for name, value in outcome.metrics.items():
            metric_samples[name].append(value)
        shortfall_count += outcome.cash_shortfall

    if metric_samples is None:
        raise RuntimeError("A positive sample_count must produce simulation outcomes.")

    summaries: dict[str, MetricSummary] = {}
    for name, observations in metric_samples.items():
        values = np.asarray(observations, dtype=np.float64)
        with np.errstate(over="ignore", invalid="ignore"):
            mean = _finite(float(np.mean(values)), f"mean for metric {name}")
            standard_error = _finite(
                float(np.std(values, ddof=1) / sqrt(metadata.sample_count)),
                f"standard error for metric {name}",
            )
            quantile_values = np.quantile(values, levels, method="linear")
        summaries[name] = MetricSummary(
            mean=mean,
            quantiles={
                level: _finite(float(value), f"quantile for metric {name}")
                for level, value in zip(
                    levels,
                    quantile_values,
                    strict=True,
                )
            },
            standard_error=standard_error,
            converged=(
                metadata.sample_count >= minimum_sample_count
                and standard_error <= tolerances[name]
            ),
        )

    probability = shortfall_count / metadata.sample_count
    probability_standard_error = sqrt(
        probability * (1 - probability) / metadata.sample_count
    )
    return MonteCarloResult(
        metadata=metadata,
        metrics=summaries,
        shortfall_probability=probability,
        shortfall_probability_standard_error=probability_standard_error,
        shortfall_probability_converged=(
            metadata.sample_count >= minimum_sample_count
            and 0 < shortfall_count < metadata.sample_count
            and probability_standard_error <= shortfall_tolerance
        ),
    )


def _validated_metrics(metrics: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(metrics, Mapping) or not metrics:
        raise ValueError("metrics must be a non-empty mapping.")
    return {
        _metric_name(name): _finite(value, f"metric {name}")
        for name, value in metrics.items()
    }


def _metric_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Metric names must be non-empty strings.")
    return name


def _quantile_levels(levels: Sequence[float]) -> tuple[float, ...]:
    if isinstance(levels, (str, bytes)):
        raise ValueError("quantile_levels must be a sequence of probabilities.")
    try:
        converted = tuple(_finite(level, "quantile level") for level in levels)
    except TypeError as exc:
        raise ValueError("quantile_levels must be a sequence of probabilities.") from exc
    if not converted or any(not 0 <= level <= 1 for level in converted):
        raise ValueError("quantile_levels must contain probabilities in [0, 1].")
    if tuple(sorted(set(converted))) != converted:
        raise ValueError("quantile_levels must be unique and strictly increasing.")
    return converted


def _nonnegative_finite(value: float, name: str) -> float:
    number = _finite(value, name)
    if number < 0:
        raise ValueError(f"{name} must be non-negative.")
    return number


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not bool.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number
