from copy import deepcopy

import pytest
from backend.arthlens.domain.simulation import SimulationMetadata
from backend.arthlens.simulation.financial import run_financial_uncertainty_analysis


def _projection():
    return {
        "initial_quantity": 100,
        "monthly_growth_rate": 0,
        "seasonality_factors": [1],
        "price_per_unit_by_month": [100],
        "variable_cost_per_unit_by_month": [50],
        "operating_expenses_by_month": [2000],
        "debt_service_by_month": [2000],
        "taxes_by_month": [0],
        "other_payments_by_month": [0],
        "subsidy_cash_release_by_month": [0],
        "working_capital_need_by_month": [0],
        "opening_working_capital_need": 0,
        "equity": 0,
        "disbursed_loan": 0,
        "capex": 0,
        "days_inventory": 0,
        "days_receivable": 0,
        "days_payable": 0,
    }


def _run(seed=19, projection=None, distributions=None):
    return run_financial_uncertainty_analysis(
        projection_inputs=projection or _projection(),
        distributions=distributions or [{
            "parameter": "price_per_unit_by_month.1",
            "distribution": "UNIFORM",
            "parameters": {"low": 50, "high": 150},
        }],
        sensitivity_parameter_values={"price_per_unit_by_month.1": [80, 120]},
        metadata=SimulationMetadata(
            scenario_id="scenario-1",
            model_version="financial-simulation-test-v1",
            seed=seed,
            sample_count=200,
            data_versions=("quantity:input-v1",),
        ),
        quantile_levels=(0.1, 0.5, 0.9),
        minimum_sample_count=100,
        convergence_tolerances={
            "total_revenue": 100,
            "total_debt_service": 0,
            "minimum_cash": 100,
        },
        shortfall_probability_tolerance=0.1,
    )


def test_financial_monte_carlo_is_reproducible_and_reports_cash_shortfall():
    first = _run()
    second = _run()

    assert first == second
    assert first.monte_carlo.metadata.seed == 19
    assert first.monte_carlo.metrics["total_revenue"].quantiles[0.5] == pytest.approx(10000, abs=1200)
    assert 0 < first.monte_carlo.shortfall_probability < 1
    assert first.monte_carlo.metrics["minimum_cash"].standard_error > 0


def test_financial_sensitivity_evaluates_alternatives_against_deterministic_projection():
    result = _run()

    assert result.sensitivity.baseline_outputs["total_revenue"] == 10000
    price_points = [point for point in result.sensitivity.points if point.parameter == "price_per_unit_by_month.1"]
    assert [point.deltas["total_revenue"] for point in price_points] == [-2000, 2000]
    assert [point.deltas["minimum_cash"] for point in price_points] == [-1000, 0]


@pytest.mark.parametrize(
    "distribution",
    [
        {
            "parameter": "price_per_unit_by_month.1",
            "distribution": "NORMAL",
            "parameters": {"mean": 100, "standard_deviation": 3},
        },
        {
            "parameter": "price_per_unit_by_month.1",
            "distribution": "TRIANGULAR",
            "parameters": {"left": 80, "mode": 100, "right": 120},
        },
    ],
)
def test_financial_monte_carlo_accepts_explicit_normal_and_triangular_distributions(distribution):
    result = _run(distributions=[distribution])
    assert result.monte_carlo.metrics["total_revenue"].mean == pytest.approx(10000, abs=400)


def test_financial_simulation_rejects_missing_unrelated_and_invalid_inputs():
    with pytest.raises(ValueError, match="shape mismatch"):
        _run(projection={"price_per_unit_by_month": [100]})

    with pytest.raises(ValueError, match="Unknown financial parameter path"):
        run_financial_uncertainty_analysis(
            projection_inputs=_projection(),
            distributions=[{
                "parameter": "not_a_financial_input",
                "distribution": "UNIFORM",
                "parameters": {"low": 1, "high": 2},
            }],
            sensitivity_parameter_values={"price_per_unit_by_month.1": [90]},
            metadata=_run().monte_carlo.metadata,
            quantile_levels=(0.5,),
            minimum_sample_count=100,
            convergence_tolerances={
                "total_revenue": 1,
                "total_debt_service": 1,
                "minimum_cash": 1,
            },
            shortfall_probability_tolerance=1,
        )

    invalid_projection = deepcopy(_projection())
    invalid_projection["monthly_growth_rate"] = -1
    with pytest.raises(ValueError, match="greater than -1"):
        _run(projection=invalid_projection)
