"""Parameterized loan amortization with explicit moratorium and subsidy treatments."""

from dataclasses import dataclass
from enum import Enum
from math import expm1, fsum, isfinite, log1p


class MoratoriumInterestTreatment(str, Enum):
    PAID = "PAID"
    CAPITALISED = "CAPITALISED"


class SubsidyTreatment(str, Enum):
    ADJUSTS_PRINCIPAL = "ADJUSTS_PRINCIPAL"
    BACK_ENDED_RELEASE = "BACK_ENDED_RELEASE"
    LOCKED_DEPOSIT = "LOCKED_DEPOSIT"


@dataclass(frozen=True)
class LoanTerms:
    principal: float
    annual_rate: float
    repayment_months: int
    moratorium_months: int
    moratorium_interest_treatment: MoratoriumInterestTreatment
    subsidy_amount: float
    subsidy_treatment: SubsidyTreatment
    subsidy_release_month: int | None

    def __post_init__(self) -> None:
        principal = _finite_number(self.principal, "principal")
        annual_rate = _finite_number(self.annual_rate, "annual_rate")
        subsidy_amount = _finite_number(self.subsidy_amount, "subsidy_amount")
        if principal < 0:
            raise ValueError("principal must be non-negative.")
        if annual_rate < 0:
            raise ValueError("annual_rate must be non-negative.")
        if subsidy_amount < 0 or subsidy_amount > principal:
            raise ValueError("subsidy_amount must be between zero and principal.")
        if (
            not isinstance(self.repayment_months, int)
            or isinstance(self.repayment_months, bool)
            or self.repayment_months <= 0
        ):
            raise ValueError("repayment_months must be a positive integer.")
        if (
            not isinstance(self.moratorium_months, int)
            or isinstance(self.moratorium_months, bool)
            or self.moratorium_months < 0
        ):
            raise ValueError("moratorium_months must be a non-negative integer.")
        try:
            moratorium_treatment = MoratoriumInterestTreatment(
                self.moratorium_interest_treatment
            )
            subsidy_treatment = SubsidyTreatment(self.subsidy_treatment)
        except ValueError as exc:
            raise ValueError(f"Unsupported loan treatment: {exc}") from exc

        release_month = self.subsidy_release_month
        if subsidy_treatment == SubsidyTreatment.ADJUSTS_PRINCIPAL:
            if release_month is not None:
                raise ValueError("ADJUSTS_PRINCIPAL subsidy cannot specify a release month.")
        elif (
            not isinstance(release_month, int)
            or isinstance(release_month, bool)
            or not 1 <= release_month <= self.moratorium_months + self.repayment_months
        ):
            raise ValueError(
                "Back-ended and locked-deposit subsidies require a valid 1-based release month."
            )

        object.__setattr__(self, "principal", principal)
        object.__setattr__(self, "annual_rate", annual_rate)
        object.__setattr__(self, "subsidy_amount", subsidy_amount)
        object.__setattr__(self, "moratorium_interest_treatment", moratorium_treatment)
        object.__setattr__(self, "subsidy_treatment", subsidy_treatment)


@dataclass(frozen=True)
class LoanScheduleRow:
    month: int
    opening_balance: float
    interest: float
    principal_paid: float
    subsidy_principal_adjustment: float
    subsidy_cash_release: float
    debt_service: float
    closing_balance: float


@dataclass(frozen=True)
class LoanSchedule:
    terms: LoanTerms
    financed_principal: float
    rows: tuple[LoanScheduleRow, ...]
    total_repaid: float


def equal_monthly_installment(principal: float, annual_rate: float, months: int) -> float:
    """Return EMI using an annual rate as a decimal fraction and an explicit term."""
    principal_value = _finite_number(principal, "principal")
    annual_rate_value = _finite_number(annual_rate, "annual_rate")
    if principal_value < 0 or annual_rate_value < 0:
        raise ValueError("principal and annual_rate must be non-negative.")
    if not isinstance(months, int) or isinstance(months, bool) or months <= 0:
        raise ValueError("months must be a positive integer.")
    if principal_value == 0:
        return 0.0
    monthly_rate = annual_rate_value / 12
    if monthly_rate == 0:
        return principal_value / months
    denominator = -expm1(-months * log1p(monthly_rate))
    payment = principal_value * monthly_rate / denominator
    if not isfinite(payment):
        raise ValueError("Loan inputs produce a non-finite monthly installment.")
    return payment


def build_loan_schedule(terms: LoanTerms) -> LoanSchedule:
    """Build monthly opening/interest/principal/closing rows from explicit terms."""
    if not isinstance(terms, LoanTerms):
        raise TypeError("terms must be a LoanTerms instance.")

    balance = terms.principal
    financed_principal = balance
    if terms.subsidy_treatment == SubsidyTreatment.ADJUSTS_PRINCIPAL:
        balance -= terms.subsidy_amount
        financed_principal = balance

    monthly_rate = terms.annual_rate / 12
    rows: list[LoanScheduleRow] = []
    installment: float | None = None
    for month in range(1, terms.moratorium_months + terms.repayment_months + 1):
        opening_balance = balance
        principal_adjustment = 0.0
        cash_release = 0.0

        if (
            terms.subsidy_treatment == SubsidyTreatment.BACK_ENDED_RELEASE
            and month == terms.subsidy_release_month
        ):
            if terms.subsidy_amount > balance:
                raise ValueError(
                    "Back-ended subsidy exceeds the outstanding principal at its release month."
                )
            principal_adjustment = terms.subsidy_amount
            balance -= principal_adjustment
            if month > terms.moratorium_months:
                remaining_months = terms.moratorium_months + terms.repayment_months - month + 1
                installment = equal_monthly_installment(
                    balance,
                    terms.annual_rate,
                    remaining_months,
                )
        elif (
            terms.subsidy_treatment == SubsidyTreatment.LOCKED_DEPOSIT
            and month == terms.subsidy_release_month
        ):
            cash_release = terms.subsidy_amount

        interest = balance * monthly_rate
        if not isfinite(interest):
            raise ValueError("Loan inputs produce non-finite monthly interest.")

        if month <= terms.moratorium_months:
            principal_paid = 0.0
            if terms.moratorium_interest_treatment == MoratoriumInterestTreatment.PAID:
                debt_service = interest
            else:
                balance += interest
                debt_service = 0.0
        else:
            if installment is None:
                installment = equal_monthly_installment(
                    balance,
                    terms.annual_rate,
                    terms.repayment_months,
                )
            if month == terms.moratorium_months + terms.repayment_months:
                debt_service = balance + interest
            else:
                debt_service = min(installment, balance + interest)
            principal_paid = debt_service - interest
            if principal_paid < 0:
                raise ValueError("Monthly installment does not cover accrued interest.")
            balance -= principal_paid
            if month == terms.moratorium_months + terms.repayment_months:
                balance = 0.0

        rows.append(
            LoanScheduleRow(
                month=month,
                opening_balance=opening_balance,
                interest=interest,
                principal_paid=principal_paid,
                subsidy_principal_adjustment=principal_adjustment,
                subsidy_cash_release=cash_release,
                debt_service=debt_service,
                closing_balance=balance,
            )
        )

    if rows and rows[-1].closing_balance != 0:
        raise ArithmeticError("Loan schedule did not amortize to a zero final balance.")
    return LoanSchedule(
        terms=terms,
        financed_principal=financed_principal,
        rows=tuple(rows),
        total_repaid=fsum(row.debt_service for row in rows),
    )


def _finite_number(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric.") from exc
    if not isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number
