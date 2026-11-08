from dataclasses import replace

import pytest
from backend.arthlens.finance import (
    FinancialScenario,
    LoanTerms,
    MoratoriumInterestTreatment,
    SubsidyTreatment,
    build_loan_schedule,
    calculate_dscr,
    calculate_financial_shortfall,
    calculate_repayment_capacity,
    calculate_working_capital_requirement,
    equal_monthly_installment,
    project_monthly_cash_flow,
)


def _loan_terms(
    *,
    principal=1200,
    annual_rate=0,
    repayment_months=3,
    moratorium_months=0,
    interest_treatment=MoratoriumInterestTreatment.PAID,
    subsidy_amount=0,
    subsidy_treatment=SubsidyTreatment.ADJUSTS_PRINCIPAL,
    subsidy_release_month=None,
):
    return LoanTerms(
        principal=principal,
        annual_rate=annual_rate,
        repayment_months=repayment_months,
        moratorium_months=moratorium_months,
        moratorium_interest_treatment=interest_treatment,
        subsidy_amount=subsidy_amount,
        subsidy_treatment=subsidy_treatment,
        subsidy_release_month=subsidy_release_month,
    )


def _financial_scenario(
    *,
    equity=1000,
    disbursed_loan=0,
    capex=500,
    variable_costs=(40, 40, 40),
    working_capital_needs=(50, 80, 40),
    opening_working_capital_need=0,
):
    return FinancialScenario(
        initial_quantity=10,
        monthly_growth_rate=0.1,
        seasonality_factors=(1, 0.5),
        price_per_unit_by_month=(100, 100, 100),
        variable_cost_per_unit_by_month=variable_costs,
        operating_expenses_by_month=(200, 200, 200),
        debt_service_by_month=(100, 100, 100),
        taxes_by_month=(0, 0, 0),
        other_payments_by_month=(0, 0, 0),
        subsidy_cash_release_by_month=(0, 0, 0),
        working_capital_need_by_month=working_capital_needs,
        opening_working_capital_need=opening_working_capital_need,
        equity=equity,
        disbursed_loan=disbursed_loan,
        capex=capex,
        days_inventory=10,
        days_receivable=20,
        days_payable=5,
    )


def test_zero_rate_loan_has_hand_calculated_moratorium_and_amortization_schedule():
    schedule = build_loan_schedule(
        _loan_terms(
            principal=1200,
            repayment_months=3,
            moratorium_months=2,
        )
    )

    assert [row.debt_service for row in schedule.rows] == [0, 0, 400, 400, 400]
    assert [row.closing_balance for row in schedule.rows] == [1200, 1200, 800, 400, 0]
    assert schedule.total_repaid == 1200
    assert schedule.rows[-1].closing_balance == 0


def test_positive_rate_emi_matches_hand_formula_and_fully_amortizes():
    payment = equal_monthly_installment(12_000, 0.12, 12)
    schedule = build_loan_schedule(
        _loan_terms(
            principal=12_000,
            annual_rate=0.12,
            repayment_months=12,
        )
    )

    assert payment == pytest.approx(1066.185464, rel=1e-8)
    assert schedule.rows[0].debt_service == pytest.approx(payment)
    assert schedule.total_repaid >= 12_000
    assert schedule.rows[-1].closing_balance == 0


def test_capitalized_and_paid_moratorium_interests_are_distinct():
    paid = build_loan_schedule(
        _loan_terms(
            annual_rate=0.12,
            repayment_months=12,
            moratorium_months=2,
            interest_treatment=MoratoriumInterestTreatment.PAID,
        )
    )
    capitalized = build_loan_schedule(
        _loan_terms(
            annual_rate=0.12,
            repayment_months=12,
            moratorium_months=2,
            interest_treatment=MoratoriumInterestTreatment.CAPITALISED,
        )
    )

    assert paid.rows[0].debt_service == pytest.approx(12)
    assert paid.rows[0].closing_balance == 1200
    assert capitalized.rows[0].debt_service == 0
    assert capitalized.rows[0].closing_balance == pytest.approx(1212)
    assert capitalized.rows[1].closing_balance == pytest.approx(1224.12)
    assert capitalized.rows[-1].closing_balance == 0


def test_subsidy_treatments_are_explicit_and_have_distinct_schedule_effects():
    upfront = build_loan_schedule(
        _loan_terms(
            principal=1000,
            repayment_months=2,
            subsidy_amount=100,
            subsidy_treatment=SubsidyTreatment.ADJUSTS_PRINCIPAL,
        )
    )
    back_ended = build_loan_schedule(
        _loan_terms(
            principal=1000,
            repayment_months=3,
            subsidy_amount=200,
            subsidy_treatment=SubsidyTreatment.BACK_ENDED_RELEASE,
            subsidy_release_month=2,
        )
    )
    locked = build_loan_schedule(
        _loan_terms(
            principal=1000,
            repayment_months=2,
            subsidy_amount=100,
            subsidy_treatment=SubsidyTreatment.LOCKED_DEPOSIT,
            subsidy_release_month=1,
        )
    )

    assert upfront.financed_principal == 900
    assert upfront.rows[-1].closing_balance == 0
    assert back_ended.rows[1].subsidy_principal_adjustment == 200
    assert back_ended.rows[-1].closing_balance == 0
    assert locked.rows[0].subsidy_cash_release == 100
    assert locked.rows[0].closing_balance == 500
    assert locked.total_repaid == 1000


def test_emi_increases_with_principal_and_rate():
    assert equal_monthly_installment(1000, 0.1, 12) > equal_monthly_installment(100, 0.1, 12)
    assert equal_monthly_installment(100, 0.2, 12) > equal_monthly_installment(100, 0.1, 12)


def test_loan_inputs_reject_invalid_terms_and_subsidy_timing():
    with pytest.raises(ValueError, match="principal must be non-negative"):
        _loan_terms(principal=-1)
    with pytest.raises(ValueError, match="repayment_months must be a positive integer"):
        _loan_terms(repayment_months=0)
    with pytest.raises(ValueError, match="valid 1-based release month"):
        _loan_terms(
            subsidy_treatment=SubsidyTreatment.BACK_ENDED_RELEASE,
            subsidy_release_month=None,
        )
    with pytest.raises(ValueError, match="exceeds the outstanding principal"):
        build_loan_schedule(
            _loan_terms(
                principal=1000,
                repayment_months=2,
                subsidy_amount=900,
                subsidy_treatment=SubsidyTreatment.BACK_ENDED_RELEASE,
                subsidy_release_month=2,
            )
        )


def test_monthly_projection_matches_explicit_cash_flow_and_working_capital_inputs():
    projection = project_monthly_cash_flow(_financial_scenario())

    assert projection.initial_cash == 500
    assert projection.cash_conversion_cycle_days == 25
    assert [month.quantity for month in projection.months] == pytest.approx([10, 5.5, 12.1])
    assert [month.cash_flow for month in projection.months] == pytest.approx([250, 0, 466])
    assert [month.closing_cash for month in projection.months] == pytest.approx([750, 750, 1216])
    assert [month.working_capital_change for month in projection.months] == [50, 30, -40]
    assert [month.break_even_quantity for month in projection.months] == pytest.approx(
        [200 / 60] * 3
    )
    assert projection.total_debt_service == 300
    assert [month.cash_available_for_debt_service for month in projection.months] == pytest.approx(
        [350, 100, 566]
    )
    assert [month.dscr for month in projection.months] == pytest.approx([3.5, 1.0, 5.66])
    assert projection.minimum_dscr == pytest.approx(1.0)
    assert projection.first_shortfall_month is None


def test_working_capital_requirement_uses_only_explicit_balance_inputs():
    assert calculate_working_capital_requirement(1200, 800, 500) == 1500
    assert calculate_working_capital_requirement(0, 0, 500) == -500
    with pytest.raises(ValueError, match="must be non-negative"):
        calculate_working_capital_requirement(-1, 0, 0)


def test_dscr_is_undefined_without_debt_service_and_preserves_negative_coverage():
    assert calculate_dscr(500, 100) == 5
    assert calculate_dscr(500, 0) is None
    assert calculate_dscr(-50, 100) == -0.5


def test_repayment_capacity_uses_explicit_coverage_rate_and_term():
    capacity = calculate_repayment_capacity(1000, 2, 0.12, 12)

    assert capacity.monthly_debt_service == 500
    assert capacity.supported_principal == pytest.approx(5627.53874, rel=1e-6)
    with pytest.raises(ValueError, match="minimum_dscr must be greater than zero"):
        calculate_repayment_capacity(1000, 0, 0.12, 12)


def test_financial_shortfall_reports_only_the_explicit_cash_deficit():
    assert calculate_financial_shortfall(-1250) == 1250
    assert calculate_financial_shortfall(0) == 0
    assert calculate_financial_shortfall(300) == 0


def test_opening_working_capital_is_an_explicit_projection_input():
    zero_opening = project_monthly_cash_flow(_financial_scenario())
    explicit_opening = project_monthly_cash_flow(
        _financial_scenario(opening_working_capital_need=50)
    )

    assert zero_opening.months[0].working_capital_change == 50
    assert explicit_opening.months[0].working_capital_change == 0
    assert explicit_opening.months[0].cash_flow == pytest.approx(
        zero_opening.months[0].cash_flow + 50
    )


def test_zero_growth_preserves_explicit_seasonality_without_growth_defaults():
    scenario = replace(
        _financial_scenario(),
        monthly_growth_rate=0,
        seasonality_factors=(1,),
    )

    projection = project_monthly_cash_flow(scenario)

    assert [month.quantity for month in projection.months] == [10, 10, 10]


def test_projection_flags_no_break_even_and_initial_cash_shortfall():
    projection = project_monthly_cash_flow(
        _financial_scenario(
            equity=0,
            disbursed_loan=0,
            capex=1000,
            variable_costs=(120, 40, 40),
        )
    )

    assert projection.first_shortfall_month == 0
    assert "CASH_SHORTFALL" in projection.quality_flags
    assert projection.months[0].break_even_quantity is None
    assert "NO_BREAK_EVEN" in projection.months[0].quality_flags


def test_zero_price_projection_keeps_no_break_even_result():
    scenario = replace(
        _financial_scenario(),
        price_per_unit_by_month=(0, 0, 0),
    )

    projection = project_monthly_cash_flow(scenario)

    assert all(month.break_even_quantity is None for month in projection.months)
    assert all("NO_BREAK_EVEN" in month.quality_flags for month in projection.months)


def test_locked_deposit_release_can_be_wired_into_monthly_cash_flow():
    scenario = replace(
        _financial_scenario(),
        subsidy_cash_release_by_month=(100, 0, 0),
    )

    projection = project_monthly_cash_flow(scenario)

    assert projection.months[0].subsidy_cash_release == 100
    assert projection.months[0].cash_flow == pytest.approx(350)


def test_financial_scenario_rejects_missing_or_inconsistent_explicit_schedules():
    with pytest.raises(ValueError, match="equal lengths"):
        FinancialScenario(
            initial_quantity=1,
            monthly_growth_rate=0,
            seasonality_factors=(1,),
            price_per_unit_by_month=(1, 1),
            variable_cost_per_unit_by_month=(0,),
            operating_expenses_by_month=(0, 0),
            debt_service_by_month=(0, 0),
            taxes_by_month=(0, 0),
            other_payments_by_month=(0, 0),
            subsidy_cash_release_by_month=(0, 0),
            working_capital_need_by_month=(0, 0),
            opening_working_capital_need=0,
            equity=0,
            disbursed_loan=0,
            capex=0,
            days_inventory=0,
            days_receivable=0,
            days_payable=0,
        )
