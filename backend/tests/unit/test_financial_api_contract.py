import pytest
from backend.arthlens.api.scenarios import (
    CalculateScenarioRequest,
    FinancialProjectionRequest,
)
from pydantic import ValidationError


def test_scenario_calculation_request_does_not_supply_numeric_financial_defaults():
    request = CalculateScenarioRequest()

    assert request.model_dump(exclude_none=True) == {}
    assert request.price_per_unit is None
    assert request.loan_principal is None
    assert request.subsidy_amount is None


def test_release_based_subsidy_requires_an_explicit_release_month():
    with pytest.raises(ValidationError, match="require an explicit subsidy_release_month"):
        CalculateScenarioRequest(
            loan_principal=1000,
            subsidy_amount=100,
            subsidy_treatment="BACK_ENDED_RELEASE",
        )


def test_subsidy_cannot_exceed_explicit_loan_principal():
    with pytest.raises(ValidationError, match="must not exceed loan_principal"):
        CalculateScenarioRequest(loan_principal=100, subsidy_amount=101)


def _projection_payload():
    return {
        "initial_quantity": 10,
        "monthly_growth_rate": 0,
        "seasonality_factors": [1],
        "price_per_unit_by_month": [100, 100],
        "variable_cost_per_unit_by_month": [50, 50],
        "operating_expenses_by_month": [200, 200],
        "debt_service_by_month": [100, 100],
        "taxes_by_month": [0, 0],
        "other_payments_by_month": [0, 0],
        "subsidy_cash_release_by_month": [0, 0],
        "working_capital_need_by_month": [100, 150],
        "opening_working_capital_need": 0,
        "equity": 1000,
        "disbursed_loan": 500,
        "capex": 300,
        "days_inventory": 10,
        "days_receivable": 20,
        "days_payable": 5,
        "minimum_dscr": 1.25,
        "repayment_capacity_annual_interest_rate": 0.12,
        "repayment_capacity_months": 24,
    }


def test_projection_contract_requires_consistent_explicit_monthly_schedules():
    payload = _projection_payload()
    payload["taxes_by_month"] = [0]

    with pytest.raises(ValidationError, match="equal lengths"):
        FinancialProjectionRequest(**payload)


def test_projection_contract_rejects_negative_monthly_values():
    payload = _projection_payload()
    payload["price_per_unit_by_month"] = [-1, 100]

    with pytest.raises(ValidationError, match="must be non-negative"):
        FinancialProjectionRequest(**payload)
