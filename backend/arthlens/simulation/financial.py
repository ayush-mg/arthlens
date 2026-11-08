"""Stochastic financial projections and deterministic scenario sensitivity."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any

from numpy.random import Generator

from backend.arthlens.domain.simulation import SimulationMetadata
from backend.arthlens.finance.projection import FinancialScenario, project_monthly_cash_flow
from backend.arthlens.simulation.monte_carlo import (
    MonteCarloResult,
    SimulationOutcome,
    run_monte_carlo,
)
from backend.arthlens.simulation.sensitivity import (
    SensitivityResult,
    run_one_at_a_time_sensitivity,
)

Distribution = Mapping[str, Any]


@dataclass(frozen=True)
class FinancialUncertaintyResult:
    monte_carlo: MonteCarloResult
    sensitivity: SensitivityResult


def run_financial_uncertainty_analysis(
    *,
    projection_inputs: Mapping[str, Any],
    distributions: Sequence[Distribution],
    sensitivity_parameter_values: Mapping[str, Sequence[float]],
    metadata: SimulationMetadata,
    quantile_levels: Sequence[float],
    minimum_sample_count: int,
    convergence_tolerances: Mapping[str, float],
    shortfall_probability_tolerance: float,
) -> FinancialUncertaintyResult:
    """Run sampled and OAT financial projections from exact user-supplied values."""
    baseline = _projection_inputs(projection_inputs)
    checked_distributions = _validate_distributions(distributions, baseline)
    checked_sensitivity = _validate_sensitivity(sensitivity_parameter_values, baseline)

    def evaluate(values: Mapping[str, float]) -> Mapping[str, float]:
        inputs = dict(baseline)
        for path, value in values.items():
            _set_path(inputs, path, value)
        projection = project_monthly_cash_flow(_financial_scenario(inputs))
        return _metrics(projection)

    baseline_parameters = {
        path: _get_path(baseline, path)
        for path in checked_sensitivity
    }
    sensitivity = run_one_at_a_time_sensitivity(
        evaluate,
        baseline_parameters=baseline_parameters,
        parameter_values=checked_sensitivity,
    )

    def sample(rng: Generator) -> SimulationOutcome:
        inputs = dict(baseline)
        for distribution in checked_distributions:
            _set_path(
                inputs,
                distribution["parameter"],
                _draw(rng, distribution["distribution"], distribution["parameters"]),
            )
        projection = project_monthly_cash_flow(_financial_scenario(inputs))
        return SimulationOutcome(
            metrics=_metrics(projection),
            cash_shortfall=projection.minimum_cash < 0,
        )

    monte_carlo = run_monte_carlo(
        sample,
        metadata=metadata,
        quantile_levels=quantile_levels,
        minimum_sample_count=minimum_sample_count,
        convergence_tolerances=convergence_tolerances,
        shortfall_probability_tolerance=shortfall_probability_tolerance,
    )
    return FinancialUncertaintyResult(monte_carlo=monte_carlo, sensitivity=sensitivity)


def _projection_inputs(values: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        raise ValueError("projection_inputs must be an object of explicit values.")
    required = set(FinancialScenario.__dataclass_fields__)
    if set(values) != required:
        missing = sorted(required - set(values))
        extra = sorted(set(values) - required)
        raise ValueError(f"projection_inputs shape mismatch; missing={missing}, extra={extra}.")
    normalized = dict(values)
    for name, value in normalized.items():
        if name in _SERIES_FIELDS:
            if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
                raise ValueError(f"{name} must be an explicit numeric series.")
            normalized[name] = list(value)
    _financial_scenario(normalized)
    return normalized


_SERIES_FIELDS = {
    "seasonality_factors",
    "price_per_unit_by_month",
    "variable_cost_per_unit_by_month",
    "operating_expenses_by_month",
    "debt_service_by_month",
    "taxes_by_month",
    "other_payments_by_month",
    "subsidy_cash_release_by_month",
    "working_capital_need_by_month",
}
_PATH_SCALAR_FIELDS = set(FinancialScenario.__dataclass_fields__) - _SERIES_FIELDS
_NONNEGATIVE_SCALARS = {
    "initial_quantity",
    "opening_working_capital_need",
    "equity",
    "disbursed_loan",
    "capex",
    "days_inventory",
    "days_receivable",
    "days_payable",
}
_METRIC_NAMES = {"total_revenue", "total_debt_service", "minimum_cash"}


def _validate_distributions(
    distributions: Sequence[Distribution],
    baseline: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    if isinstance(distributions, (str, bytes)) or not isinstance(distributions, Sequence) or not distributions:
        raise ValueError("distributions must contain at least one explicit parameter distribution.")
    checked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in distributions:
        if not isinstance(item, Mapping):
            raise ValueError("Each distribution must be an object.")
        if set(item) != {"parameter", "distribution", "parameters"}:
            raise ValueError("Each distribution requires parameter, distribution, and parameters only.")
        path = item["parameter"]
        _get_path(baseline, path)
        if path in seen:
            raise ValueError(f"Duplicate distribution for {path}.")
        seen.add(path)
        distribution = item["distribution"]
        parameters = item["parameters"]
        if distribution not in {"NORMAL", "UNIFORM", "TRIANGULAR"}:
            raise ValueError(f"Unsupported distribution for {path}: {distribution!r}.")
        expected = {
            "NORMAL": {"mean", "standard_deviation"},
            "UNIFORM": {"low", "high"},
            "TRIANGULAR": {"left", "mode", "right"},
        }[distribution]
        if not isinstance(parameters, Mapping) or set(parameters) != expected:
            raise ValueError(f"{distribution} for {path} requires exactly {sorted(expected)}.")
        numeric = {key: _finite(value, f"{path}.{key}") for key, value in parameters.items()}
        if distribution == "NORMAL" and numeric["standard_deviation"] < 0:
            raise ValueError(f"standard_deviation for {path} must be non-negative.")
        if distribution == "UNIFORM" and numeric["low"] >= numeric["high"]:
            raise ValueError(f"low for {path} must be less than high.")
        if distribution == "TRIANGULAR" and not (
            numeric["left"] <= numeric["mode"] <= numeric["right"]
            and numeric["left"] < numeric["right"]
        ):
            raise ValueError(f"TRIANGULAR bounds for {path} must satisfy left <= mode <= right and left < right.")
        _validate_possible_domain(path, distribution, numeric)
        checked.append({"parameter": path, "distribution": distribution, "parameters": numeric})
    return tuple(checked)


def _validate_sensitivity(
    parameter_values: Mapping[str, Sequence[float]],
    baseline: Mapping[str, Any],
) -> dict[str, tuple[float, ...]]:
    if not isinstance(parameter_values, Mapping) or not parameter_values:
        raise ValueError("sensitivity_parameter_values must contain explicit alternatives.")
    checked: dict[str, tuple[float, ...]] = {}
    for path, values in parameter_values.items():
        _get_path(baseline, path)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
            raise ValueError(f"Sensitivity alternatives for {path} must be a non-empty numeric sequence.")
        converted = tuple(_finite(value, f"sensitivity value for {path}") for value in values)
        for value in converted:
            _validate_domain(path, value)
        checked[path] = converted
    return checked


def _validate_possible_domain(path: str, distribution: str, params: Mapping[str, float]) -> None:
    if distribution == "NORMAL":
        return
    bounds = (params["low"], params["high"]) if distribution == "UNIFORM" else (params["left"], params["right"])
    for value in bounds:
        _validate_domain(path, value)


def _validate_domain(path: str, value: float) -> None:
    field = path.split(".", 1)[0]
    if field in _NONNEGATIVE_SCALARS or field in _SERIES_FIELDS and field != "monthly_growth_rate":
        if value < 0:
            raise ValueError(f"{path} must be non-negative.")
    if field == "monthly_growth_rate" and value <= -1:
        raise ValueError("monthly_growth_rate must be greater than -1.")


def _get_path(inputs: Mapping[str, Any], path: str) -> float:
    if not isinstance(path, str) or not path:
        raise ValueError("Financial parameter paths must be non-empty strings.")
    parts = path.split(".")
    field = parts[0]
    if field in _PATH_SCALAR_FIELDS and len(parts) == 1:
        return _finite(inputs[field], path)
    if field in _SERIES_FIELDS and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1]) - 1
        values = inputs[field]
        if not 0 <= index < len(values):
            raise ValueError(f"Financial parameter path is outside the supplied series: {path}.")
        return _finite(values[index], path)
    raise ValueError(f"Unknown financial parameter path: {path!r}.")


def _set_path(inputs: dict[str, Any], path: str, value: float) -> None:
    number = _finite(value, path)
    _validate_domain(path, number)
    parts = path.split(".")
    if parts[0] in _PATH_SCALAR_FIELDS and len(parts) == 1:
        inputs[parts[0]] = number
    elif parts[0] in _SERIES_FIELDS and len(parts) == 2 and parts[1].isdigit():
        index = int(parts[1]) - 1
        if not 0 <= index < len(inputs[parts[0]]):
            raise ValueError(f"Financial parameter path is outside the supplied series: {path}.")
        inputs[parts[0]][index] = number
    else:
        raise ValueError(f"Unknown financial parameter path: {path!r}.")


def _financial_scenario(inputs: Mapping[str, Any]) -> FinancialScenario:
    return FinancialScenario(
        **{
            key: tuple(value) if key in _SERIES_FIELDS else value
            for key, value in inputs.items()
        }
    )


def _metrics(projection: Any) -> dict[str, float]:
    return {
        "total_revenue": projection.total_revenue,
        "total_debt_service": projection.total_debt_service,
        "minimum_cash": projection.minimum_cash,
    }


def _draw(rng: Generator, distribution: str, parameters: Mapping[str, float]) -> float:
    if distribution == "NORMAL":
        value = rng.normal(parameters["mean"], parameters["standard_deviation"])
    elif distribution == "UNIFORM":
        value = rng.uniform(parameters["low"], parameters["high"])
    else:
        value = rng.triangular(parameters["left"], parameters["mode"], parameters["right"])
    return _finite(value, "sampled distribution value")


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not bool.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number
