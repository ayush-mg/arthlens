"""Deterministic working-capital, DSCR, and repayment-capacity calculations."""

from dataclasses import dataclass
from math import isfinite

from backend.arthlens.finance.loans import equal_monthly_installment


@dataclass(frozen=True)
class RepaymentCapacity:
    monthly_debt_service: float
    supported_principal: float


def calculate_working_capital_requirement(
    inventory_value: float,
    accounts_receivable: float,
    accounts_payable: float,
) -> float:
    """Return net working capital from explicit balance-sheet assumptions."""
    inventory = _nonnegative(inventory_value, "inventory_value")
    receivables = _nonnegative(accounts_receivable, "accounts_receivable")
    payables = _nonnegative(accounts_payable, "accounts_payable")
    return _finite(inventory + receivables - payables, "working_capital_requirement")


def calculate_dscr(cash_available_for_debt_service: float, debt_service: float) -> float | None:
    """Return DSCR, or None when there is no scheduled debt service to cover."""
    cash_available = _finite(
        cash_available_for_debt_service,
        "cash_available_for_debt_service",
    )
    service = _nonnegative(debt_service, "debt_service")
    if service == 0:
        return None
    return _finite(cash_available / service, "dscr")


def calculate_repayment_capacity(
    cash_available_for_debt_service: float,
    minimum_dscr: float,
    annual_interest_rate: float,
    repayment_months: int,
) -> RepaymentCapacity:
    """Compute the monthly service and loan principal supported by explicit inputs."""
    cash_available = _finite(
        cash_available_for_debt_service,
        "cash_available_for_debt_service",
    )
    coverage = _finite(minimum_dscr, "minimum_dscr")
    rate = _nonnegative(annual_interest_rate, "annual_interest_rate")
    if coverage <= 0:
        raise ValueError("minimum_dscr must be greater than zero.")
    if not isinstance(repayment_months, int) or isinstance(repayment_months, bool) or repayment_months <= 0:
        raise ValueError("repayment_months must be a positive integer.")

    monthly_capacity = max(cash_available, 0.0) / coverage
    installment_factor = equal_monthly_installment(1.0, rate, repayment_months)
    return RepaymentCapacity(
        monthly_debt_service=_finite(monthly_capacity, "monthly_debt_service_capacity"),
        supported_principal=_finite(monthly_capacity / installment_factor, "supported_principal"),
    )


def calculate_financial_shortfall(minimum_projected_cash: float) -> float:
    """Return the funding required to eliminate a projected minimum-cash deficit."""
    minimum_cash = _finite(minimum_projected_cash, "minimum_projected_cash")
    return max(-minimum_cash, 0.0)


def _nonnegative(value: float, name: str) -> float:
    number = _finite(value, name)
    if number < 0:
        raise ValueError(f"{name} must be non-negative.")
    return number


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number
