"""
Loop C: Scheme Eligibility, Working-Capital Projection & Verified Report Generation.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 2.3, 6.4-6.8, 8.8).
Phase: P5-1 (End-to-End Workflow Loops).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import uuid4

from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.finance.loans import (
    LoanTerms,
    MoratoriumInterestTreatment,
    SubsidyTreatment,
    build_loan_schedule,
)
from backend.arthlens.finance.projection import (
    FinancialProjection,
    FinancialScenario,
    calculate_break_even_quantity,
    project_monthly_cash_flow,
)
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.reports import (
    VerifiedReport,
    build_verified_report,
    export_report_csv,
    export_report_json,
)
from backend.arthlens.policy.rules import TruthValue


@dataclass(frozen=True)
class LoopCResult:
    scheme_eligibility_status: TruthValue
    break_even_quantity: float
    projection_summary: FinancialProjection
    verified_report: VerifiedReport
    report_json: str
    report_csv: str
    quantities: tuple[Quantity, ...]
    calculation_provenance: dict[str, Any]


def run_loop_c_scheme_viability(
    ledger: Ledger,
    *,
    owner_id: str,
    geo_unit_id: str,
    resolution: ResolutionTier,
    project_cost_inr: float,
    promoter_contribution_fraction: float,
    subsidy_fraction: float,
    annual_interest_rate: float,
    loan_term_months: int,
    moratorium_months: int,
    moratorium_interest_treatment: MoratoriumInterestTreatment,
    subsidy_treatment: SubsidyTreatment,
    subsidy_release_month: int | None,
    unit_price: float,
    unit_variable_cost: float,
    fixed_operating_costs_monthly: float,
    monthly_sales_units: float,
    monthly_growth_rate: float,
    seasonality_factors: tuple[float, ...],
    taxes_by_month: tuple[float, ...],
    other_payments_by_month: tuple[float, ...],
    working_capital_need_by_month: tuple[float, ...],
    opening_working_capital_need: float,
    days_inventory: float,
    days_receivable: float,
    days_payable: float,
) -> LoopCResult:
    """
    Execute Loop C: Evaluate scheme eligibility, build the explicitly sized loan and cash-flow model,
    register epistemic quantities into ledger, and build a verified analytical report.
    """
    resolution = ResolutionTier(resolution)
    if not owner_id.strip() or not geo_unit_id.strip():
        raise ValueError("Explicit owner_id and geo_unit_id are required.")
    for name, fraction in (
        ("promoter_contribution_fraction", promoter_contribution_fraction),
        ("subsidy_fraction", subsidy_fraction),
    ):
        if not 0 <= fraction <= 1:
            raise ValueError(f"{name} must be between zero and one.")
    if project_cost_inr <= 0:
        raise ValueError("project_cost_inr must be greater than zero.")
    if unit_price <= unit_variable_cost:
        raise ValueError("unit_price must exceed unit_variable_cost for break-even analysis.")
    # Scheme rules are never inferred here. Loop C has no approved rule version or
    # rule-specific evidence mapping, so eligibility remains explicitly UNKNOWN.
    eligibility_status = TruthValue.UNKNOWN

    # 2. Compute break-even units
    break_even_units = calculate_break_even_quantity(
        price_per_unit=unit_price,
        variable_cost_per_unit=unit_variable_cost,
        fixed_costs=fixed_operating_costs_monthly,
    )
    if break_even_units is None:
        raise ValueError("Price must exceed variable cost to establish break-even.")

    # 3. Model loan schedule from explicit financing terms.
    loan_principal = project_cost_inr * (1.0 - promoter_contribution_fraction)
    subsidy_amount = project_cost_inr * subsidy_fraction
    loan_terms = LoanTerms(
        principal=loan_principal,
        annual_rate=annual_interest_rate,
        repayment_months=loan_term_months,
        moratorium_months=moratorium_months,
        moratorium_interest_treatment=moratorium_interest_treatment,
        subsidy_amount=subsidy_amount,
        subsidy_treatment=subsidy_treatment,
        subsidy_release_month=subsidy_release_month,
    )
    schedule = build_loan_schedule(loan_terms)

    # 4. Project monthly cash flows & working capital (CCC)
    horizon = len(schedule.rows)
    debt_service_series = tuple(row.debt_service for row in schedule.rows)
    subsidy_release_series = tuple(row.subsidy_cash_release for row in schedule.rows)

    scenario = FinancialScenario(
        initial_quantity=monthly_sales_units,
        monthly_growth_rate=monthly_growth_rate,
        seasonality_factors=seasonality_factors,
        price_per_unit_by_month=(unit_price,) * horizon,
        variable_cost_per_unit_by_month=(unit_variable_cost,) * horizon,
        operating_expenses_by_month=(fixed_operating_costs_monthly,) * horizon,
        debt_service_by_month=debt_service_series,
        taxes_by_month=taxes_by_month,
        other_payments_by_month=other_payments_by_month,
        subsidy_cash_release_by_month=subsidy_release_series,
        working_capital_need_by_month=working_capital_need_by_month,
        opening_working_capital_need=opening_working_capital_need,
        equity=project_cost_inr * promoter_contribution_fraction,
        disbursed_loan=loan_principal,
        capex=project_cost_inr,
        days_inventory=days_inventory,
        days_receivable=days_receivable,
        days_payable=days_payable,
    )
    projection = project_monthly_cash_flow(scenario)

    # 5. Register numeric assumptions and trace calculations through their inputs.
    today = date.today().isoformat()
    numeric_inputs: dict[str, tuple[float, str]] = {
        "project_cost_inr": (project_cost_inr, "INR"),
        "promoter_contribution_fraction": (promoter_contribution_fraction, "dimensionless"),
        "subsidy_fraction": (subsidy_fraction, "dimensionless"),
        "annual_interest_rate": (annual_interest_rate, "dimensionless/year"),
        "loan_term_months": (float(loan_term_months), "month"),
        "moratorium_months": (float(moratorium_months), "month"),
        "unit_price": (unit_price, "INR/count"),
        "unit_variable_cost": (unit_variable_cost, "INR/count"),
        "fixed_operating_costs_monthly": (fixed_operating_costs_monthly, "INR/month"),
        "monthly_sales_units": (monthly_sales_units, "count/month"),
        "monthly_growth_rate": (monthly_growth_rate, "dimensionless/month"),
        "opening_working_capital_need": (opening_working_capital_need, "INR"),
        "days_inventory": (days_inventory, "day"),
        "days_receivable": (days_receivable, "day"),
        "days_payable": (days_payable, "day"),
    }
    if subsidy_release_month is not None:
        numeric_inputs["subsidy_release_month"] = (float(subsidy_release_month), "month")
    numeric_inputs.update(
        {
            f"seasonality_factors.{index + 1}": (value, "dimensionless")
            for index, value in enumerate(seasonality_factors)
        }
    )
    numeric_inputs.update(
        {f"taxes_by_month.{index + 1}": (value, "INR/month") for index, value in enumerate(taxes_by_month)}
    )
    numeric_inputs.update(
        {f"other_payments_by_month.{index + 1}": (value, "INR/month") for index, value in enumerate(other_payments_by_month)}
    )
    numeric_inputs.update(
        {
            f"working_capital_need_by_month.{index + 1}": (value, "INR")
            for index, value in enumerate(working_capital_need_by_month)
        }
    )

    assumption_quantities: dict[str, Quantity] = {}
    for name, (value, unit) in numeric_inputs.items():
        quantity = Quantity(
            id=str(uuid4()),
            definition_key=f"finance.assumption.{name}",
            value=float(value),
            unit=unit,
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id=geo_unit_id,
            resolution=resolution,
            as_of=today,
            uncertainty="EXACT",
            source_refs=((f"user:{owner_id}", f"loop_c/input:{name}", today),),
            method_id="explicit_user_input",
            model_version="1",
            owner_id=owner_id,
        )
        ledger.register(quantity)
        assumption_quantities[name] = quantity

    loan_principal_q = Quantity(
        id=str(uuid4()),
        definition_key="finance.loan_principal",
        value=loan_principal,
        unit="INR",
        kind=Kind.CALCULATED,
        evidence_floor=3,
        geo_unit_id=geo_unit_id,
        resolution=resolution,
        as_of=today,
        source_refs=(),
        method_id="finance:project_cost_less_promoter_contribution_v1",
        model_version="arthlens-finance-v1",
        parent_ids=(
            assumption_quantities["project_cost_inr"].id,
            assumption_quantities["promoter_contribution_fraction"].id,
        ),
        owner_id=owner_id,
    )
    subsidy_amount_q = Quantity(
        id=str(uuid4()),
        definition_key="finance.subsidy_amount_assumption",
        value=subsidy_amount,
        unit="INR",
        kind=Kind.CALCULATED,
        evidence_floor=3,
        geo_unit_id=geo_unit_id,
        resolution=resolution,
        as_of=today,
        source_refs=(),
        method_id="finance:explicit_subsidy_fraction_v1",
        model_version="arthlens-finance-v1",
        parent_ids=(
            assumption_quantities["project_cost_inr"].id,
            assumption_quantities["subsidy_fraction"].id,
        ),
        owner_id=owner_id,
    )
    ledger.register(loan_principal_q)
    ledger.register(subsidy_amount_q)

    be_qty = Quantity(
        id=str(uuid4()),
        definition_key="finance.break_even_quantity",
        value=round(break_even_units, 2),
        unit="count/month",
        kind=Kind.CALCULATED,
        evidence_floor=3,
        geo_unit_id=geo_unit_id,
        resolution=resolution,
        as_of=today,
        uncertainty="EXACT",
        source_refs=(),
        method_id="finance:break_even_v1",
        model_version="arthlens-finance-v1",
        parent_ids=(
            assumption_quantities["unit_price"].id,
            assumption_quantities["unit_variable_cost"].id,
            assumption_quantities["fixed_operating_costs_monthly"].id,
        ),
        owner_id=owner_id,
    )
    ledger.register(be_qty)

    loan_parent_ids = [
        loan_principal_q.id,
        subsidy_amount_q.id,
        assumption_quantities["annual_interest_rate"].id,
        assumption_quantities["loan_term_months"].id,
        assumption_quantities["moratorium_months"].id,
    ]
    if subsidy_release_month is not None:
        loan_parent_ids.append(assumption_quantities["subsidy_release_month"].id)
    debt_service_quantities = []
    for row in schedule.rows:
        debt_service_q = Quantity(
            id=str(uuid4()),
            definition_key=f"finance.loan_schedule.debt_service.month_{row.month}",
            value=row.debt_service,
            unit="INR/month",
            kind=Kind.CALCULATED,
            evidence_floor=3,
            geo_unit_id=geo_unit_id,
            resolution=resolution,
            as_of=today,
            source_refs=(),
            method_id="finance:loan_schedule_v1",
            model_version="arthlens-finance-v1",
            parent_ids=tuple(loan_parent_ids),
            owner_id=owner_id,
        )
        ledger.register(debt_service_q)
        debt_service_quantities.append(debt_service_q)

    if projection.minimum_dscr is None:
        raise ValueError("INSUFFICIENT_DATA: the explicit loan schedule has no positive debt service for DSCR.")
    has_shortfall = projection.first_shortfall_month is not None
    dscr_parent_names = [
        "monthly_sales_units",
        "monthly_growth_rate",
        "unit_price",
        "unit_variable_cost",
        "fixed_operating_costs_monthly",
        "opening_working_capital_need",
    ]
    dscr_parent_names.extend(
        name
        for name in assumption_quantities
        if name.startswith(("seasonality_factors.", "taxes_by_month.", "other_payments_by_month.", "working_capital_need_by_month."))
    )
    dscr_parent_ids = [assumption_quantities[name].id for name in dscr_parent_names]
    dscr_parent_ids.extend(quantity.id for quantity in debt_service_quantities)
    dscr_qty = Quantity(
        id=str(uuid4()),
        definition_key="finance.debt_service_coverage_ratio",
        value=projection.minimum_dscr,
        unit="dimensionless",
        kind=Kind.CALCULATED,
        evidence_floor=3,
        geo_unit_id=geo_unit_id,
        resolution=resolution,
        as_of=today,
        uncertainty="EXACT",
        source_refs=(),
        method_id="finance:monthly_minimum_dscr_v1",
        model_version="arthlens-finance-v1",
        parent_ids=tuple(dscr_parent_ids),
        owner_id=owner_id,
    )
    ledger.register(dscr_qty)

    # 6. Build verified analytical report
    template = (
        "ArthLens Financial Viability Assessment:\n"
        "- Scheme Eligibility: UNKNOWN — approved policy rule/version and evidence are required\n"
        f"- Monthly Break-Even Quantity: {{{{q:{be_qty.id}}}}}\n"
        f"- Debt Service Coverage Ratio: {{{{q:{dscr_qty.id}}}}}\n"
        f"- Cash Shortfall Detected: {has_shortfall}"
    )

    verified_report = build_verified_report(template, ledger)
    report_json = export_report_json(verified_report)
    report_csv = export_report_csv(verified_report)
    calculation_provenance = {
        "model_id": "arthlens-finance-v1",
        "parameters": {
            "owner_id": owner_id,
            "geo_unit_id": geo_unit_id,
            "resolution": int(resolution),
            "project_cost_inr": project_cost_inr,
            "promoter_contribution_fraction": promoter_contribution_fraction,
            "subsidy_fraction": subsidy_fraction,
            "annual_interest_rate": annual_interest_rate,
            "loan_term_months": loan_term_months,
            "moratorium_months": moratorium_months,
            "moratorium_interest_treatment": MoratoriumInterestTreatment(
                moratorium_interest_treatment
            ).value,
            "subsidy_treatment": SubsidyTreatment(subsidy_treatment).value,
            "subsidy_release_month": subsidy_release_month,
            "monthly_growth_rate": monthly_growth_rate,
            "seasonality_factors": list(seasonality_factors),
        },
        "input_quantity_ids": {name: quantity.id for name, quantity in assumption_quantities.items()},
        "loan_schedule_debt_service_quantity_ids": [
            quantity.id for quantity in debt_service_quantities
        ],
        "output_quantity_ids": {
            "break_even_quantity": be_qty.id,
            "debt_service_coverage_ratio": dscr_qty.id,
        },
        "output_parent_quantity_ids": {
            "break_even_quantity": list(be_qty.parent_ids),
            "debt_service_coverage_ratio": list(dscr_qty.parent_ids),
        },
        "eligibility": {
            "outcome": eligibility_status.value,
            "status": "RULE_UNAVAILABLE",
            "reason": "No approved effective-dated policy rule version and linked evidence were supplied.",
            "official_award_decision": False,
        },
    }

    return LoopCResult(
        scheme_eligibility_status=eligibility_status,
        break_even_quantity=break_even_units,
        projection_summary=projection,
        verified_report=verified_report,
        report_json=report_json,
        report_csv=report_csv,
        quantities=(be_qty, dscr_qty),
        calculation_provenance=calculation_provenance,
    )


__all__ = ["LoopCResult", "run_loop_c_scheme_viability"]
