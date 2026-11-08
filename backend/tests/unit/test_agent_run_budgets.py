from decimal import Decimal

import pytest
from backend.arthlens.agent.budgets import RunBudgetLimits, RunBudgetReservation


def test_run_budget_limits_accept_handbook_defaults():
    limits = RunBudgetLimits()

    assert limits.max_steps == 25
    assert limits.max_replans == 3
    assert limits.max_model_calls == 30
    assert limits.max_cost_usd == Decimal("0.25")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_steps": -1},
        {"max_replans": True},
        {"max_model_calls": -1},
        {"max_cost_usd": Decimal("NaN")},
        {"max_cost_usd": Decimal("0.00001")},
        {"max_cost_usd": -0.01},
    ],
)
def test_run_budget_limits_reject_invalid_values(kwargs):
    with pytest.raises(ValueError):
        RunBudgetLimits(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"steps": -1},
        {"steps": True},
        {"model_calls": -1},
        {"cost_usd": Decimal("-0.01")},
        {"cost_usd": Decimal("NaN")},
        {"cost_usd": Decimal("0.00001")},
        {},
    ],
)
def test_budget_reservation_rejects_invalid_or_empty_usage(kwargs):
    with pytest.raises(ValueError):
        RunBudgetReservation(**kwargs)


def test_budget_reservation_normalizes_decimal_input():
    reservation = RunBudgetReservation(steps=1, cost_usd=0.0123)

    assert reservation.cost_usd == Decimal("0.0123")
