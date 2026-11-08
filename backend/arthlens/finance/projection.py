"""Deterministic monthly cash-flow projection from explicit scenario inputs."""

from dataclasses import dataclass
from math import fsum, isfinite

from backend.arthlens.finance.analysis import calculate_dscr


@dataclass(frozen=True)
class FinancialScenario:
    initial_quantity: float
    monthly_growth_rate: float
    seasonality_factors: tuple[float, ...]
    price_per_unit_by_month: tuple[float, ...]
    variable_cost_per_unit_by_month: tuple[float, ...]
    operating_expenses_by_month: tuple[float, ...]
    debt_service_by_month: tuple[float, ...]
    taxes_by_month: tuple[float, ...]
    other_payments_by_month: tuple[float, ...]
    subsidy_cash_release_by_month: tuple[float, ...]
    working_capital_need_by_month: tuple[float, ...]
    opening_working_capital_need: float
    equity: float
    disbursed_loan: float
    capex: float
    days_inventory: float
    days_receivable: float
    days_payable: float

    def __post_init__(self) -> None:
        initial_quantity = _nonnegative(self.initial_quantity, "initial_quantity")
        growth = _finite(self.monthly_growth_rate, "monthly_growth_rate")
        if growth <= -1:
            raise ValueError("monthly_growth_rate must be greater than -1.")
        object.__setattr__(self, "initial_quantity", initial_quantity)
        object.__setattr__(self, "monthly_growth_rate", growth)

        seasonality = _series(self.seasonality_factors, "seasonality_factors")
        if not seasonality:
            raise ValueError("seasonality_factors must not be empty.")
        if any(value < 0 for value in seasonality):
            raise ValueError("Seasonality factors must be non-negative.")
        object.__setattr__(self, "seasonality_factors", seasonality)

        series_names = (
            "price_per_unit_by_month",
            "variable_cost_per_unit_by_month",
            "operating_expenses_by_month",
            "debt_service_by_month",
            "taxes_by_month",
            "other_payments_by_month",
            "subsidy_cash_release_by_month",
            "working_capital_need_by_month",
        )
        series = {
            name: _series(getattr(self, name), name)
            for name in series_names
        }
        horizon = len(series["price_per_unit_by_month"])
        if horizon == 0:
            raise ValueError("Monthly financial schedules must contain at least one period.")
        if any(len(values) != horizon for values in series.values()):
            raise ValueError("All monthly financial schedules must have equal lengths.")
        for name, values in series.items():
            if any(value < 0 for value in values):
                raise ValueError(f"{name} values must be non-negative.")
            object.__setattr__(self, name, values)

        for name in ("equity", "disbursed_loan", "capex"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name))
        object.__setattr__(
            self,
            "opening_working_capital_need",
            _nonnegative(self.opening_working_capital_need, "opening_working_capital_need"),
        )
        for name in ("days_inventory", "days_receivable", "days_payable"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name))


@dataclass(frozen=True)
class FinancialMonth:
    month: int
    quantity: float
    revenue: float
    cost_of_goods_sold: float
    contribution_per_unit: float
    break_even_quantity: float | None
    operating_expenses: float
    debt_service: float
    taxes: float
    other_payments: float
    subsidy_cash_release: float
    working_capital_need: float
    working_capital_change: float
    cash_available_for_debt_service: float
    dscr: float | None
    cash_flow: float
    opening_cash: float
    closing_cash: float
    quality_flags: frozenset[str]


@dataclass(frozen=True)
class FinancialProjection:
    initial_cash: float
    cash_conversion_cycle_days: float
    months: tuple[FinancialMonth, ...]
    total_revenue: float
    total_debt_service: float
    minimum_dscr: float | None
    minimum_cash: float
    first_shortfall_month: int | None
    quality_flags: frozenset[str]


def project_monthly_cash_flow(scenario: FinancialScenario) -> FinancialProjection:
    """Run a deterministic projection; all payment, tax, and working-capital inputs are explicit."""
    if not isinstance(scenario, FinancialScenario):
        raise TypeError("scenario must be a FinancialScenario instance.")

    initial_cash = _finite(
        scenario.equity + scenario.disbursed_loan - scenario.capex,
        "initial_cash",
    )
    cash_conversion_cycle = _finite(
        scenario.days_inventory + scenario.days_receivable - scenario.days_payable,
        "cash_conversion_cycle_days",
    )
    cash = initial_cash
    previous_working_capital_need = scenario.opening_working_capital_need
    months: list[FinancialMonth] = []
    flags: set[str] = set()
    first_shortfall_month = 0 if initial_cash < 0 else None

    horizon = len(scenario.price_per_unit_by_month)
    for index in range(horizon):
        try:
            quantity = (
                scenario.initial_quantity
                * (1 + scenario.monthly_growth_rate) ** index
                * scenario.seasonality_factors[index % len(scenario.seasonality_factors)]
            )
        except OverflowError as exc:
            raise ValueError(f"Quantity forecast overflows in month {index + 1}.") from exc
        quantity = _nonnegative(quantity, f"quantity forecast for month {index + 1}")

        price = scenario.price_per_unit_by_month[index]
        variable_cost = scenario.variable_cost_per_unit_by_month[index]
        revenue = _finite(quantity * price, f"revenue for month {index + 1}")
        cost_of_goods_sold = _finite(
            quantity * variable_cost,
            f"cost of goods sold for month {index + 1}",
        )
        contribution = price - variable_cost
        break_even_quantity = calculate_break_even_quantity(
            price,
            variable_cost,
            scenario.operating_expenses_by_month[index],
        )
        month_flags = set() if break_even_quantity is not None else {"NO_BREAK_EVEN"}

        working_capital_need = scenario.working_capital_need_by_month[index]
        working_capital_change = working_capital_need - previous_working_capital_need
        cash_available_for_debt_service = _finite(
            revenue
            - cost_of_goods_sold
            - scenario.operating_expenses_by_month[index]
            - scenario.taxes_by_month[index]
            - scenario.other_payments_by_month[index]
            - working_capital_change,
            f"cash available for debt service in month {index + 1}",
        )
        debt_service = scenario.debt_service_by_month[index]
        dscr = calculate_dscr(cash_available_for_debt_service, debt_service)
        cash_flow = _finite(
            cash_available_for_debt_service
            - debt_service
            + scenario.subsidy_cash_release_by_month[index],
            f"cash flow for month {index + 1}",
        )
        opening_cash = cash
        cash = _finite(cash + cash_flow, f"cash balance for month {index + 1}")
        if opening_cash < 0 or cash < 0:
            month_flags.add("CASH_SHORTFALL")
            flags.add("CASH_SHORTFALL")
            if first_shortfall_month is None:
                first_shortfall_month = index + 1
        flags.update(month_flags)
        months.append(
            FinancialMonth(
                month=index + 1,
                quantity=quantity,
                revenue=revenue,
                cost_of_goods_sold=cost_of_goods_sold,
                contribution_per_unit=contribution,
                break_even_quantity=break_even_quantity,
                operating_expenses=scenario.operating_expenses_by_month[index],
                debt_service=scenario.debt_service_by_month[index],
                taxes=scenario.taxes_by_month[index],
                other_payments=scenario.other_payments_by_month[index],
                subsidy_cash_release=scenario.subsidy_cash_release_by_month[index],
                working_capital_need=working_capital_need,
                working_capital_change=working_capital_change,
                cash_available_for_debt_service=cash_available_for_debt_service,
                dscr=dscr,
                cash_flow=cash_flow,
                opening_cash=opening_cash,
                closing_cash=cash,
                quality_flags=frozenset(month_flags),
            )
        )
        previous_working_capital_need = working_capital_need

    return FinancialProjection(
        initial_cash=initial_cash,
        cash_conversion_cycle_days=cash_conversion_cycle,
        months=tuple(months),
        total_revenue=fsum(month.revenue for month in months),
        total_debt_service=fsum(month.debt_service for month in months),
        minimum_dscr=min(
            (month.dscr for month in months if month.dscr is not None),
            default=None,
        ),
        minimum_cash=min([initial_cash, *(month.closing_cash for month in months)]),
        first_shortfall_month=first_shortfall_month,
        quality_flags=frozenset(flags),
    )


def calculate_break_even_quantity(
    price_per_unit: float,
    variable_cost_per_unit: float,
    fixed_costs: float,
) -> float | None:
    """Return break-even units, or None when contribution is not positive."""
    price = _nonnegative(price_per_unit, "price_per_unit")
    variable_cost = _nonnegative(variable_cost_per_unit, "variable_cost_per_unit")
    fixed_cost = _nonnegative(fixed_costs, "fixed_costs")
    contribution = price - variable_cost
    if contribution <= 0:
        return None
    return _finite(fixed_cost / contribution, "break_even_quantity")


def _series(values: tuple[float, ...], name: str) -> tuple[float, ...]:
    try:
        converted = tuple(_finite(value, name) for value in values)
    except TypeError as exc:
        raise ValueError(f"{name} must be a sequence of numbers.") from exc
    return converted


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
