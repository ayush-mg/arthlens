from backend.arthlens.decision.additional_models import (
    evaluate_business_expansion,
    evaluate_business_viability,
    evaluate_cash_flow_pressure,
    evaluate_cost_reduction,
    evaluate_customer_credit_risk,
    evaluate_financing_comparison,
    evaluate_inventory_procurement,
    evaluate_location_selection,
)
from backend.arthlens.domain.business import DecisionOutcome


def test_financing_comparison_uses_user_offers_and_exposes_each_alternative():
    result = evaluate_financing_comparison({
        "purchase_cost": "10000", "monthly_operating_gain": "2000", "available_cash": "20000",
        "loan_interest_rate_pct": "12", "loan_term_months": "24",
        "lease_monthly_payment": "1000", "lease_term_months": "24",
        "equity_injection": "2000", "discount_rate_pct": "8",
    })

    assert result.model_id == "FINANCING_COMPARISON"
    assert len(result.alternatives) == 3
    assert result.recommended_alternative in {"LOAN", "LEASE", "EQUITY"}
    assert all("npv" in item.metrics for item in result.alternatives)


def test_cash_pressure_does_not_count_receivables_before_stated_collection():
    result = evaluate_cash_flow_pressure({
        "cash_balance": "100", "monthly_cash_inflows": "0", "monthly_cash_outflows": "0",
        "receivables_due_30d": "500", "receivables_collectible_amount": "250",
        "payables_due_30d": "300", "payables_deferral_amount": "100",
        "credit_line_available": "400", "credit_line_draw_amount": "200",
        "credit_line_interest_pct": "12", "monthly_survival_threshold": "50",
    })

    cases = {item.alternative_id: item.metrics["projected_30d_cash"] for item in result.alternatives}
    assert cases["BASE"] == -200
    assert cases["COLLECT"] == 50
    assert cases["DEFER"] == -100
    assert cases["CREDIT"] == -2
    assert result.outcome == DecisionOutcome.FEASIBLE


def test_cost_reduction_reports_payback_and_user_stated_horizon():
    result = evaluate_cost_reduction({
        "cost_category": "utilities", "current_monthly_cost": "1000", "proposed_monthly_cost": "700",
        "one_time_implementation_cost": "600", "expected_quality_cost_monthly": "50",
        "evaluation_months": "12",
    })

    assert result.calculations["monthly_net_savings"] == 250.0
    assert result.calculations["payback_months"] == 2.4
    assert result.outcome == DecisionOutcome.FEASIBLE


def test_credit_risk_blocks_sale_that_exceeds_limit():
    result = evaluate_customer_credit_risk({
        "customer_name": "Customer A", "current_receivable": "900", "credit_limit": "1000",
        "requested_sale_amount": "200", "average_monthly_sales": "500",
        "gross_margin_pct": "30", "default_risk_pct": "5", "annual_cost_of_capital_pct": "12",
        "proposed_terms_days": "30", "overdue_days": "0",
    })

    assert result.outcome == DecisionOutcome.NOT_FEASIBLE
    assert result.constraints[0].passed is False


def test_inventory_procurement_uses_reorder_and_lead_time_inputs():
    result = evaluate_inventory_procurement({
        "unit_cost": "10", "order_quantity": "40", "monthly_demand": "90", "current_stock": "10",
        "reorder_threshold": "30", "holding_cost_per_unit_month": "0.25",
        "stockout_cost_per_unit": "5", "supplier_lead_time_days": "10",
    })

    assert result.calculations["purchase_cash"] == 400.0
    assert result.calculations["coverage_days_before_order"] == 3.3
    assert result.outcome == DecisionOutcome.FEASIBLE


def test_location_selection_ranks_only_explicit_candidate_assumptions():
    result = evaluate_location_selection({"candidates": [
        {"location_name": "North", "fitout_capex": "10000", "monthly_rent": "1000", "monthly_staff_cost": "500",
         "catchment_monthly_demand": "1000", "conversion_rate_pct": "5", "average_order_value": "100",
         "gross_margin_pct": "40", "cannibalization_pct": "10"},
        {"location_name": "South", "fitout_capex": "8000", "monthly_rent": "800", "monthly_staff_cost": "400",
         "catchment_monthly_demand": "700", "conversion_rate_pct": "4", "average_order_value": "100",
         "gross_margin_pct": "35", "cannibalization_pct": "15"},
    ]})

    assert result.alternatives[0].name == "North"
    assert result.alternatives[0].metrics["monthly_net_contribution"] == 300.0
    assert result.recommended_alternative == "LOCATION_1"


def test_business_expansion_surfaces_unfunded_capex():
    result = evaluate_business_expansion({
        "expansion_capex": "50000", "projected_monthly_revenue": "20000", "gross_margin_pct": "40",
        "projected_monthly_opex": "5000", "available_cash": "10000",
        "committed_financing": "5000", "financing_mode": "MIXED",
    })

    assert result.calculations["funding_gap"] == 35000.0
    assert result.outcome == DecisionOutcome.NOT_FEASIBLE


def test_business_viability_has_twelve_month_cash_projection_and_dscr():
    result = evaluate_business_viability({
        "current_monthly_revenue": "20000", "variable_cost_pct": "50",
        "monthly_fixed_costs": "5000", "cash_balance": "15000",
        "monthly_debt_service": "1000", "current_working_capital": "7000",
        "monthly_revenue_growth_pct": "1", "annual_interest_rate_pct": "12",
        "monthly_capex": "0", "current_debt": "10000",
    })

    assert result.calculations["debt_service_coverage_ratio"] == 5.0
    assert result.calculations["minimum_projected_cash"] > 0
    assert result.outcome == DecisionOutcome.FEASIBLE
