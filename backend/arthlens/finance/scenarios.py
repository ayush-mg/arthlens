"""Deterministic scenario cases, sensitivity analysis, and reproducible Monte Carlo."""

from __future__ import annotations

import random
from statistics import fmean, pstdev
from typing import Any, Mapping

from backend.arthlens.finance.projection import FinancialScenario, project_monthly_cash_flow
from backend.arthlens.finance.loans import equal_monthly_installment

SCENARIO_MODEL_VERSION = "1.0"
_REQUIRED = (
    "horizon_months",
    "initial_quantity",
    "monthly_volume_growth_rate",
    "selling_price",
    "variable_cost_per_unit",
    "fixed_monthly_operating_expenses",
    "opening_cash",
)
_NONNEGATIVE = {
    "initial_quantity", "selling_price", "variable_cost_per_unit",
    "fixed_monthly_operating_expenses", "monthly_debt_service", "monthly_taxes",
    "monthly_other_payments", "monthly_subsidy_cash_release",
    "monthly_working_capital_need", "opening_working_capital_need", "opening_cash",
    "equity", "disbursed_loan", "capex", "days_inventory", "days_receivable", "days_payable",
    "loan_interest_rate_pct", "loan_tenure_months", "lease_payment_monthly",
}
_SENSITIVITY_DRIVERS = (
    "initial_quantity", "selling_price", "variable_cost_per_unit",
    "fixed_monthly_operating_expenses", "monthly_debt_service", "monthly_working_capital_need",
)
_ALLOWED = set(_REQUIRED) | _NONNEGATIVE | {
    "monthly_volume_growth_rate", "annual_discount_rate", "seasonality_factors",
    "cases", "distributions", "financing_mode",
}


def validate_assumptions(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("Scenario assumptions must be a JSON object.")
    missing = [name for name in _REQUIRED if name not in raw]
    if missing:
        raise ValueError(f"Missing required scenario assumptions: {', '.join(missing)}")
    extra = set(raw) - _ALLOWED
    if extra:
        raise ValueError(f"Unsupported scenario assumptions: {', '.join(sorted(extra))}")
    normalized: dict[str, Any] = {}
    try:
        horizon = int(raw["horizon_months"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("horizon_months must be an integer from 12 to 36.") from exc
    if horizon < 12 or horizon > 36:
        raise ValueError("horizon_months must be between 12 and 36.")
    normalized["horizon_months"] = horizon
    for key in (_NONNEGATIVE | {"monthly_volume_growth_rate", "annual_discount_rate"}) & set(raw):
        try:
            value = float(raw[key])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{key} must be numeric.") from exc
        if not (value == value and abs(value) != float("inf")):
            raise ValueError(f"{key} must be finite.")
        if key in _NONNEGATIVE and value < 0:
            raise ValueError(f"{key} must be non-negative.")
        if key == "monthly_volume_growth_rate" and value <= -1:
            raise ValueError("monthly_volume_growth_rate must be greater than -1.")
        if key == "annual_discount_rate" and value <= -1:
            raise ValueError("annual_discount_rate must be greater than -100%.")
        normalized[key] = value
    seasonality = raw.get("seasonality_factors", [1.0])
    if not isinstance(seasonality, (list, tuple)) or not seasonality:
        raise ValueError("seasonality_factors must be a non-empty array.")
    try:
        seasonality_values = [float(value) for value in seasonality]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("seasonality_factors must contain finite numbers.") from exc
    if any(not (value == value and abs(value) != float("inf")) or value < 0 for value in seasonality_values):
        raise ValueError("seasonality_factors must contain finite non-negative values.")
    normalized["seasonality_factors"] = seasonality_values
    if raw.get("financing_mode") is not None:
        financing_mode = str(raw["financing_mode"]).upper()
        if financing_mode not in {"OWN_CAPITAL", "LOAN", "LEASE", "MIXED"}:
            raise ValueError("financing_mode must be OWN_CAPITAL, LOAN, LEASE, or MIXED.")
        normalized["financing_mode"] = financing_mode
    if "loan_tenure_months" in normalized:
        if not normalized["loan_tenure_months"].is_integer() or normalized["loan_tenure_months"] <= 0:
            raise ValueError("loan_tenure_months must be a positive whole number.")
    financing_mode = normalized.get("financing_mode")
    if financing_mode == "LOAN":
        loan_fields = ("disbursed_loan", "loan_interest_rate_pct", "loan_tenure_months")
        missing_loan_fields = [field for field in loan_fields if field not in normalized]
        if missing_loan_fields:
            raise ValueError(f"LOAN financing requires explicit assumptions: {', '.join(missing_loan_fields)}")
    if financing_mode == "LEASE" and not normalized.get("lease_payment_monthly"):
        raise ValueError("LEASE financing requires a positive lease_payment_monthly assumption.")
    if financing_mode == "OWN_CAPITAL" and "capex" in normalized:
        available = normalized["opening_cash"] + normalized.get("equity", 0.0)
        if normalized["capex"] > available:
            raise ValueError("Own-capital capex exceeds the scenario's explicit opening cash plus equity injection.")
    cases = raw.get("cases", {})
    if not isinstance(cases, Mapping) or set(cases) - {"optimistic", "pessimistic"}:
        raise ValueError("cases may contain only optimistic and pessimistic override objects.")
    normalized_cases: dict[str, dict[str, float]] = {}
    for case_name, overrides in cases.items():
        if not isinstance(overrides, Mapping):
            raise ValueError(f"{case_name} case must be an object of explicit driver assumptions.")
        allowed_case_drivers = _REQUIRED[1:] + ("monthly_volume_growth_rate",) + tuple(_NONNEGATIVE - {"monthly_volume_growth_rate"})
        if set(overrides) - set(allowed_case_drivers):
            raise ValueError(f"{case_name} case includes an unsupported driver.")
        candidate = dict(normalized)
        candidate.update(overrides)
        normalized_cases[case_name] = {
            key: validate_assumptions({**candidate, "cases": {}, "distributions": {}})[key]
            for key in overrides
        }
    distributions = raw.get("distributions", {})
    if not isinstance(distributions, Mapping):
        raise ValueError("distributions must be an object keyed by scenario driver.")
    allowed_dist_drivers = set(_SENSITIVITY_DRIVERS) | {"monthly_volume_growth_rate"}
    if set(distributions) - allowed_dist_drivers:
        raise ValueError("A distribution references an unsupported scenario driver.")
    normalized_distributions = {key: _validate_distribution(key, value) for key, value in distributions.items()}
    normalized["cases"] = normalized_cases
    normalized["distributions"] = normalized_distributions
    return normalized


def _validate_distribution(driver: str, raw: Mapping[str, Any]) -> dict[str, float | str]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"Distribution for {driver} must be an object.")
    kind = str(raw.get("distribution", "")).upper()
    fields = {
        "NORMAL": ("mean", "std_dev"),
        "UNIFORM": ("min_val", "max_val"),
        "TRIANGULAR": ("low", "mode", "high"),
        "PERT": ("min_val", "mode", "max_val"),
    }
    if kind not in fields:
        raise ValueError(f"Unsupported distribution for {driver}: {kind}.")
    expected = set(fields[kind]) | {"distribution"}
    if kind == "PERT":
        expected.add("lambda_param")
    if set(raw) - expected:
        raise ValueError(f"Unexpected distribution parameters for {driver}.")
    result: dict[str, float | str] = {"distribution": kind}
    for field in fields[kind]:
        try:
            value = float(raw[field])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Distribution parameter {field} for {driver} must be numeric.") from exc
        if not (value == value and abs(value) != float("inf")):
            raise ValueError(f"Distribution parameter {field} for {driver} must be finite.")
        result[field] = value
    if kind == "NORMAL" and result["std_dev"] < 0:
        raise ValueError("Normal distribution std_dev must be non-negative.")
    if kind == "UNIFORM" and result["min_val"] > result["max_val"]:
        raise ValueError("Uniform distribution min_val must not exceed max_val.")
    if kind in {"TRIANGULAR", "PERT"}:
        low, mode, high = result.get("low", result.get("min_val")), result["mode"], result.get("high", result.get("max_val"))
        if not low <= mode <= high or low == high:
            raise ValueError(f"{kind.title()} distribution requires low <= mode <= high and low < high.")
    if kind == "PERT":
        result["lambda_param"] = float(raw.get("lambda_param", 4.0))
        if result["lambda_param"] <= 0:
            raise ValueError("PERT lambda_param must be positive.")
    return result


def _sample(rng: random.Random, config: Mapping[str, Any]) -> float:
    kind = config["distribution"]
    if kind == "NORMAL":
        return rng.gauss(config["mean"], config["std_dev"])
    if kind == "UNIFORM":
        return rng.uniform(config["min_val"], config["max_val"])
    if kind == "TRIANGULAR":
        return rng.triangular(config["low"], config["high"], config["mode"])
    low, mode, high = config["min_val"], config["mode"], config["max_val"]
    weight = config.get("lambda_param", 4.0)
    alpha = 1 + weight * (mode - low) / (high - low)
    beta = 1 + weight * (high - mode) / (high - low)
    return low + rng.betavariate(alpha, beta) * (high - low)


def _project(assumptions: Mapping[str, Any], overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    drivers = dict(assumptions)
    drivers.update(overrides or {})
    drivers = validate_assumptions({**drivers, "cases": {}, "distributions": {}})
    horizon = drivers["horizon_months"]
    lease_payment = drivers.get("lease_payment_monthly", 0.0)
    if drivers.get("monthly_debt_service") is not None:
        debt_service = [drivers["monthly_debt_service"] + lease_payment] * horizon
    elif drivers.get("loan_tenure_months") and drivers.get("disbursed_loan", 0.0) > 0:
        installment = equal_monthly_installment(
            drivers["disbursed_loan"],
            drivers.get("loan_interest_rate_pct", 0.0) / 100,
            int(drivers["loan_tenure_months"]),
        )
        debt_service = [installment * (month <= drivers["loan_tenure_months"]) + lease_payment for month in range(1, horizon + 1)]
    else:
        debt_service = [lease_payment] * horizon
    projection = project_monthly_cash_flow(FinancialScenario(
        initial_quantity=drivers["initial_quantity"],
        monthly_growth_rate=drivers.get("monthly_volume_growth_rate", 0.0),
        seasonality_factors=tuple(drivers["seasonality_factors"]),
        price_per_unit_by_month=(drivers["selling_price"],) * horizon,
        variable_cost_per_unit_by_month=(drivers["variable_cost_per_unit"],) * horizon,
        operating_expenses_by_month=(drivers["fixed_monthly_operating_expenses"],) * horizon,
        debt_service_by_month=tuple(debt_service),
        taxes_by_month=(drivers.get("monthly_taxes", 0.0),) * horizon,
        other_payments_by_month=(drivers.get("monthly_other_payments", 0.0),) * horizon,
        subsidy_cash_release_by_month=(drivers.get("monthly_subsidy_cash_release", 0.0),) * horizon,
        working_capital_need_by_month=(drivers.get("monthly_working_capital_need", 0.0),) * horizon,
        opening_working_capital_need=drivers.get("opening_working_capital_need", 0.0),
        equity=drivers.get("equity", 0.0),
        disbursed_loan=drivers.get("disbursed_loan", 0.0),
        capex=drivers.get("capex", 0.0),
        days_inventory=drivers.get("days_inventory", 0.0),
        days_receivable=drivers.get("days_receivable", 0.0),
        days_payable=drivers.get("days_payable", 0.0),
        opening_cash=drivers["opening_cash"],
    ))
    net_profit_by_month = [month.revenue - month.cost_of_goods_sold - month.operating_expenses - month.taxes for month in projection.months]
    total_net_profit = sum(net_profit_by_month)
    discount = drivers.get("annual_discount_rate", 0.0)
    monthly_rate = (1 + discount) ** (1 / 12) - 1
    npv = sum(value / ((1 + monthly_rate) ** month) for month, value in enumerate(net_profit_by_month, start=1)) - drivers.get("capex", 0.0)
    ending_cash = projection.months[-1].closing_cash
    return {
        "months": [{
            "month": month.month,
            "revenue": round(month.revenue, 2),
            "cost_of_goods_sold": round(month.cost_of_goods_sold, 2),
            "net_profit": round(net_profit_by_month[month.month - 1], 2),
            "cash_flow": round(month.cash_flow, 2),
            "closing_cash": round(month.closing_cash, 2),
            "dscr": None if month.dscr is None else round(month.dscr, 6),
        } for month in projection.months],
        "summary": {
            "total_revenue": round(projection.total_revenue, 2),
            "total_net_profit": round(total_net_profit, 2),
            "ending_cash": round(ending_cash, 2),
            "minimum_cash": round(projection.minimum_cash, 2),
            "npv": round(npv, 2),
            "minimum_dscr": None if projection.minimum_dscr is None else round(projection.minimum_dscr, 6),
            "first_shortfall_month": projection.first_shortfall_month,
            "cash_conversion_cycle_days": round(projection.cash_conversion_cycle_days, 2),
            "quality_flags": sorted(projection.quality_flags),
        },
    }


def _case_overrides(assumptions: Mapping[str, Any], case: str) -> Mapping[str, Any]:
    return assumptions.get("cases", {}).get(case, {}) if case != "base" else {}


def run_scenario(assumptions: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_assumptions(assumptions)
    cases = {name: _project(validated, _case_overrides(validated, name)) for name in ("base", "optimistic", "pessimistic")}
    tornado: list[dict[str, Any]] = []
    for driver in _SENSITIVITY_DRIVERS:
        if driver not in validated:
            continue
        base_value = validated[driver]
        if not base_value:
            continue
        impact: dict[str, Any] = {"driver": driver, "variations": []}
        for pct in (-0.2, -0.1, 0.1, 0.2):
            shifted = base_value * (1 + pct)
            if driver in _NONNEGATIVE:
                shifted = max(0.0, shifted)
            projection = _project(validated, {driver: shifted})["summary"]
            impact["variations"].append({
                "change_pct": pct * 100,
                "total_net_profit": projection["total_net_profit"],
                "ending_cash": projection["ending_cash"],
                "npv": projection["npv"],
            })
        impact["max_net_profit_impact"] = round(max(abs(item["total_net_profit"] - cases["base"]["summary"]["total_net_profit"]) for item in impact["variations"]), 2)
        tornado.append(impact)
    tornado.sort(key=lambda item: item["max_net_profit_impact"], reverse=True)
    return {"model_version": SCENARIO_MODEL_VERSION, "cases": cases, "sensitivity_tornado": tornado}


def run_monte_carlo(
    assumptions: Mapping[str, Any],
    distribution_config: Mapping[str, Any],
    iterations: int,
    random_seed: int,
) -> dict[str, Any]:
    validated = validate_assumptions({**assumptions, "distributions": distribution_config})
    if isinstance(iterations, bool) or not 1 <= iterations <= 100000:
        raise ValueError("iterations must be between 1 and 100000.")
    if isinstance(random_seed, bool) or not 0 <= random_seed <= (2**64 - 1):
        raise ValueError("random_seed must be an unsigned 64-bit integer.")
    if not validated["distributions"]:
        raise ValueError("At least one driver distribution is required for Monte Carlo.")
    rng = random.Random(random_seed)
    results: dict[str, list[float]] = {key: [] for key in ("total_net_profit", "ending_cash", "npv")}
    losses = 0
    cash_shortfalls = 0
    for _ in range(iterations):
        sampled: dict[str, float] = {}
        for driver, config in validated["distributions"].items():
            value = _sample(rng, config)
            if driver in _NONNEGATIVE:
                value = max(0.0, value)
            elif driver == "monthly_volume_growth_rate":
                value = max(-0.999999, value)
            sampled[driver] = value
        summary = _project(validated, sampled)["summary"]
        for metric in results:
            results[metric].append(float(summary[metric]))
        losses += summary["total_net_profit"] < 0
        cash_shortfalls += summary["minimum_cash"] < 0
    summaries: dict[str, Any] = {}
    for metric, values in results.items():
        ordered = sorted(values)
        def percentile(p: float) -> float:
            position = (len(ordered) - 1) * p
            lower = int(position)
            upper = min(lower + 1, len(ordered) - 1)
            fraction = position - lower
            return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 2)
        summaries[metric] = {
            "mean": round(fmean(values), 2),
            "std_dev": round(pstdev(values), 2),
            "p10": percentile(0.10), "p25": percentile(0.25), "p50": percentile(0.50),
            "p75": percentile(0.75), "p90": percentile(0.90),
        }
    return {
        "model_version": SCENARIO_MODEL_VERSION,
        "iterations": iterations,
        "random_seed": random_seed,
        "distributions": validated["distributions"],
        "metrics": summaries,
        "probability_of_loss": round(losses / iterations, 6),
        "probability_of_cash_shortfall": round(cash_shortfalls / iterations, 6),
    }
