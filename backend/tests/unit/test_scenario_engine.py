import pytest

from backend.arthlens.finance.scenarios import run_monte_carlo, run_scenario, validate_assumptions


BASE = {
    "horizon_months": 12,
    "initial_quantity": 1000,
    "monthly_volume_growth_rate": 0.01,
    "selling_price": 100,
    "variable_cost_per_unit": 55,
    "fixed_monthly_operating_expenses": 20000,
    "opening_cash": 50000,
    "monthly_debt_service": 3000,
    "annual_discount_rate": 0.12,
    "cases": {
        "optimistic": {"monthly_volume_growth_rate": 0.02},
        "pessimistic": {"monthly_volume_growth_rate": -0.01},
    },
}


@pytest.mark.parametrize(
    "distribution",
    [
        {"distribution": "NORMAL", "mean": 0.01, "std_dev": 0.003},
        {"distribution": "UNIFORM", "min_val": 0.0, "max_val": 0.02},
        {"distribution": "TRIANGULAR", "low": 0.0, "mode": 0.01, "high": 0.02},
        {"distribution": "PERT", "min_val": 0.0, "mode": 0.01, "max_val": 0.02, "lambda_param": 4},
    ],
)
def test_monte_carlo_is_seeded_and_replayable(distribution):
    first = run_monte_carlo(BASE, {"monthly_volume_growth_rate": distribution}, 50, 9321)
    replay = run_monte_carlo(BASE, {"monthly_volume_growth_rate": distribution}, 50, 9321)
    assert first == replay
    assert set(first["metrics"]["ending_cash"]) == {"mean", "std_dev", "p10", "p25", "p50", "p75", "p90"}
    assert 0 <= first["probability_of_loss"] <= 1
    assert 0 <= first["probability_of_cash_shortfall"] <= 1


def test_scenario_cases_and_sensitivity_use_explicit_inputs():
    result = run_scenario(BASE)
    assert len(result["cases"]["base"]["months"]) == 12
    assert result["cases"]["optimistic"]["summary"]["total_net_profit"] > result["cases"]["pessimistic"]["summary"]["total_net_profit"]
    assert result["sensitivity_tornado"]
    assert {row["change_pct"] for row in result["sensitivity_tornado"][0]["variations"]} == {-20.0, -10.0, 10.0, 20.0}


def test_assumptions_reject_missing_or_invalid_horizon():
    with pytest.raises(ValueError, match="Missing required"):
        validate_assumptions({})
    with pytest.raises(ValueError, match="between 12 and 36"):
        validate_assumptions({**BASE, "horizon_months": 6})
