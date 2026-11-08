"""Deterministic one-at-a-time sensitivity analysis with explicit input values."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType


@dataclass(frozen=True)
class SensitivityPoint:
    parameter: str
    value: float
    outputs: Mapping[str, float]
    deltas: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))
        object.__setattr__(self, "deltas", MappingProxyType(dict(self.deltas)))


@dataclass(frozen=True)
class SensitivityResult:
    baseline_outputs: Mapping[str, float]
    points: tuple[SensitivityPoint, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "baseline_outputs",
            MappingProxyType(dict(self.baseline_outputs)),
        )


def run_one_at_a_time_sensitivity(
    evaluate: Callable[[Mapping[str, float]], Mapping[str, float]],
    *,
    baseline_parameters: Mapping[str, float],
    parameter_values: Mapping[str, Sequence[float]],
) -> SensitivityResult:
    """Evaluate explicit parameter alternatives, changing exactly one input each time."""
    if not callable(evaluate):
        raise TypeError("evaluate must be callable.")
    baseline = _numeric_mapping(baseline_parameters, "baseline_parameters")
    if not baseline:
        raise ValueError("baseline_parameters must not be empty.")
    if not isinstance(parameter_values, Mapping) or not parameter_values:
        raise ValueError("parameter_values must be a non-empty mapping.")

    baseline_outputs = _numeric_mapping(evaluate(MappingProxyType(baseline)), "baseline outputs")
    if not baseline_outputs:
        raise ValueError("evaluate must return at least one output.")

    points: list[SensitivityPoint] = []
    for parameter, values in parameter_values.items():
        if not isinstance(parameter, str) or parameter not in baseline:
            raise ValueError(f"Unknown sensitivity parameter: {parameter!r}.")
        if isinstance(values, (str, bytes)):
            raise ValueError(f"Values for {parameter} must be a sequence of numbers.")
        try:
            alternatives = tuple(_finite(value, f"value for {parameter}") for value in values)
        except TypeError as exc:
            raise ValueError(f"Values for {parameter} must be a sequence of numbers.") from exc
        if not alternatives:
            raise ValueError(f"Values for {parameter} must not be empty.")
        for value in alternatives:
            changed = dict(baseline)
            changed[parameter] = value
            outputs = _numeric_mapping(
                evaluate(MappingProxyType(changed)),
                f"outputs for {parameter}={value}",
            )
            if set(outputs) != set(baseline_outputs):
                raise ValueError("evaluate must return the same output names for every scenario.")
            points.append(
                SensitivityPoint(
                    parameter=parameter,
                    value=value,
                    outputs=outputs,
                    deltas={
                        name: _finite(
                            outputs[name] - baseline_outputs[name],
                            f"output delta for {name}",
                        )
                        for name in baseline_outputs
                    },
                )
            )
    return SensitivityResult(baseline_outputs=baseline_outputs, points=tuple(points))


def _numeric_mapping(values: Mapping[str, float], name: str) -> dict[str, float]:
    if not isinstance(values, Mapping):
        raise ValueError(f"{name} must be a mapping.")
    converted: dict[str, float] = {}
    for key, value in values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{name} keys must be non-empty strings.")
        converted[key] = _finite(value, f"{name}[{key}]")
    return converted


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
