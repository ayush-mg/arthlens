"""Additional deterministic Decimal decision evaluators for operational cases."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.arthlens.domain.business import DecisionOutcome
from backend.arthlens.decision.models import (
    DecisionAlternativeEvaluation, DecisionConstraintResult, DecisionEvaluationResult,
    DecisionGraphEdge, DecisionGraphNode, DecisionNodeType, _HUNDRED, _ONE, _ZERO,
    _decimal, _monthly_installment, _result_round, _compute_alternative_kpis,
)


def _constraint(identifier: str, label: str, passed: bool, threshold: Any, actual: Any,
                explanation: str, hard: bool = True, comparison: str = ">=") -> DecisionConstraintResult:
    return DecisionConstraintResult(identifier, label, hard, passed, threshold, actual, comparison, explanation)


def _graph(inputs: dict[str, Any], calculations: dict[str, Any], outcome: str):
    nodes = [
        DecisionGraphNode(f"input_{name}", name.replace("_", " ").title(), DecisionNodeType.INPUT,
                          value, name.replace("_", " "), "INR" if any(k in name for k in ("cost", "cash", "revenue", "payment", "amount", "value", "price")) else "")
        for name, value in inputs.items()
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
    ]
    calculation_nodes = [
        DecisionGraphNode(f"calc_{name}", name.replace("_", " ").title(), DecisionNodeType.CALCULATION, value, name.replace("_", " "))
        for name, value in calculations.items()
        if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
    ]
    nodes.extend(calculation_nodes)
    nodes.append(DecisionGraphNode("outcome", "Outcome", DecisionNodeType.OUTCOME, outcome))
    edges = [DecisionGraphEdge(node.id, calculation_nodes[0].id) for node in nodes if node.node_type == DecisionNodeType.INPUT and calculation_nodes]
    if calculation_nodes:
        edges.append(DecisionGraphEdge(calculation_nodes[-1].id, "outcome"))
    return nodes, edges


def _result(model_id: str, objective: str, inputs: dict[str, Any], calculations: dict[str, Any],
            constraints: list[DecisionConstraintResult], alternatives: list[DecisionAlternativeEvaluation],
            explanation: str, recommended: str | None) -> DecisionEvaluationResult:
    hard_pass = all(item.passed for item in constraints if item.is_hard_constraint)
    outcome = DecisionOutcome.FEASIBLE if hard_pass else DecisionOutcome.NOT_FEASIBLE
    nodes, edges = _graph(inputs, calculations, outcome.value)
    return DecisionEvaluationResult(
        model_id=model_id, model_version="1.0.0", objective=objective, inputs=inputs,
        calculations=calculations, constraints=constraints, outcome=outcome,
        summary_explanation=explanation, recommended_alternative=recommended,
        alternatives=alternatives, graph_nodes=nodes, graph_edges=edges,
    )


def evaluate_financing_comparison(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    cost = _decimal(inputs["purchase_cost"])
    gain = _decimal(inputs["monthly_operating_gain"])
    cash = _decimal(inputs["available_cash"])
    rate = _decimal(inputs["loan_interest_rate_pct"]) / _HUNDRED / Decimal("12")
    loan_months = int(_decimal(inputs["loan_term_months"]))
    lease_payment = _decimal(inputs["lease_monthly_payment"])
    lease_months = int(_decimal(inputs["lease_term_months"]))
    equity = _decimal(inputs["equity_injection"])
    discount = _decimal(inputs["discount_rate_pct"]) / _HUNDRED / Decimal("12")
    if loan_months <= 0 or lease_months <= 0:
        raise ValueError("Loan and lease terms must be greater than zero.")
    loan_principal = max(Decimal("0"), cost - equity)
    loan_emi = _monthly_installment(loan_principal, rate, loan_months)
    loan_total = loan_emi * loan_months + equity
    lease_total = lease_payment * lease_months
    equity_cash_after = cash - cost
    options = [
        ("LOAN", "Term loan", loan_total, loan_emi, cash - equity),
        ("LEASE", "Lease", lease_total, lease_payment, cash),
        ("EQUITY", "Equity purchase", cost, Decimal("0"), equity_cash_after),
    ]
    projected_options = []
    for identifier, label, total_cost, monthly_payment, ending_cash in options:
        term = loan_months if identifier == "LOAN" else lease_months if identifier == "LEASE" else max(loan_months, lease_months)
        monthly_net = gain - monthly_payment
        initial_funding = equity if identifier == "LOAN" else cost if identifier == "EQUITY" else Decimal("0")
        npv = -initial_funding
        for month in range(1, term + 1):
            discount_factor = (_ONE + discount) ** month
            npv += monthly_net / discount_factor
        option_constraints = [
            _constraint(f"{identifier}_CASH", f"{label} initial funding fits available cash",
                        ending_cash >= 0, 0, ending_cash, "Initial funding is compared with stated available cash."),
            _constraint(f"{identifier}_COVERAGE", f"{label} monthly gain covers scheduled payment",
                        monthly_net >= 0, 0, monthly_net, "Monthly operating gain is compared with the stated financing payment."),
        ]
        passed = all(item.passed for item in option_constraints)
        projected_options.append((identifier, label, total_cost, monthly_payment, ending_cash, monthly_net, npv, option_constraints, passed))
    projected_options.sort(key=lambda row: (not row[8], -row[6]))
    alternatives = []
    for rank, (identifier, label, total_cost, monthly_payment, ending_cash, monthly_net, npv, option_constraints, passed) in enumerate(projected_options, 1):
        alternatives.append(DecisionAlternativeEvaluation(
            alternative_id=identifier, name=label,
            outcome=DecisionOutcome.FEASIBLE if passed else DecisionOutcome.NOT_FEASIBLE,
            rank=rank, score=float(max(Decimal("0"), min(_HUNDRED, Decimal("100") - total_cost / max(cost, Decimal("1")) * _HUNDRED))),
            metrics={"total_cost": _result_round(total_cost, 2), "monthly_payment": _result_round(monthly_payment, 2),
                     "monthly_net_cash_flow": _result_round(monthly_net, 2), "ending_cash": _result_round(ending_cash, 2),
                     "npv": _result_round(npv, 2)},
            constraints=option_constraints,
            explanation=f"{label} total scheduled outflow: {total_cost:.2f}; monthly net cash after financing: {monthly_net:.2f}.",
        ))
    selected = next((item for item in alternatives if item.outcome == DecisionOutcome.FEASIBLE), None)
    calculations = {
        "loan_emi": _result_round(loan_emi, 2), "loan_total_cost": _result_round(loan_total, 2),
        "lease_total_cost": _result_round(lease_total, 2),
        "equity_cash_after_purchase": _result_round(equity_cash_after, 2),
        "discount_rate_monthly_pct": _result_round(discount * _HUNDRED, 4),
    }
    overall_outcome = DecisionOutcome.FEASIBLE if selected else DecisionOutcome.NOT_FEASIBLE
    nodes, edges = _graph(inputs, calculations, overall_outcome.value)
    return DecisionEvaluationResult(model_id="FINANCING_COMPARISON", model_version="1.0.0",
                   objective="Compare explicit loan, lease, and equity financing offers.",
                   inputs=inputs, calculations=calculations,
                   constraints=[item for alt in alternatives for item in alt.constraints], outcome=overall_outcome,
                   summary_explanation="Alternatives are ranked by discounted operating cash after stated financing payments. Each option shows its own cash and payment constraints.",
                   recommended_alternative=selected.alternative_id if selected else None,
                   alternatives=alternatives, graph_nodes=nodes, graph_edges=edges)


def evaluate_business_expansion(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    capex = _decimal(inputs["expansion_capex"])
    monthly_revenue = _decimal(inputs["projected_monthly_revenue"])
    margin_pct = _decimal(inputs["gross_margin_pct"])
    monthly_opex = _decimal(inputs["projected_monthly_opex"])
    cash = _decimal(inputs["available_cash"])
    financing = _decimal(inputs["committed_financing"])
    contribution = monthly_revenue * margin_pct / _HUNDRED
    monthly_net = contribution - monthly_opex
    payback = capex / monthly_net if monthly_net > 0 else Decimal("Infinity")
    funding_gap = max(Decimal("0"), capex - cash - financing)
    constraints = [
        _constraint("EXPANSION_FUNDED", "Capex is covered by available cash and committed financing", funding_gap == 0,
                    0, funding_gap, "Only funds stated as available or committed are counted."),
        _constraint("EXPANSION_POSITIVE_CONTRIBUTION", "Expansion monthly net contribution is positive", monthly_net > 0,
                    0, monthly_net, "Projected contribution must exceed projected operating expense.", comparison=">"),
    ]
    outcome = DecisionOutcome.FEASIBLE if all(item.passed for item in constraints) else DecisionOutcome.NOT_FEASIBLE
    calculations = {
        "monthly_contribution": _result_round(contribution, 2), "monthly_net_cash_flow": _result_round(monthly_net, 2),
        "payback_months": _result_round(payback, 1) if payback.is_finite() else None,
        "funding_gap": _result_round(funding_gap, 2),
    }
    alternative = DecisionAlternativeEvaluation(
        "EXPAND", "Proceed with expansion", outcome, 1, 80.0 if outcome == DecisionOutcome.FEASIBLE else 30.0,
        calculations, constraints,
        "Projection uses the submitted expansion capex, revenue, margin, operating expense, and committed funding.",
    )
    return _result("BUSINESS_EXPANSION", "Assess an explicitly funded business expansion.",
                   inputs, calculations, constraints, [alternative], alternative.explanation,
                   alternative.alternative_id if outcome == DecisionOutcome.FEASIBLE else None)


def evaluate_inventory_procurement(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    unit_cost = _decimal(inputs["unit_cost"])
    quantity = _decimal(inputs["order_quantity"])
    demand = _decimal(inputs["monthly_demand"])
    stock = _decimal(inputs["current_stock"])
    reorder = _decimal(inputs["reorder_threshold"])
    holding = _decimal(inputs["holding_cost_per_unit_month"])
    stockout_cost = _decimal(inputs["stockout_cost_per_unit"])
    lead_days = _decimal(inputs["supplier_lead_time_days"])
    if min(unit_cost, quantity, demand, stock, reorder, holding, stockout_cost, lead_days) < 0:
        raise ValueError("Inventory inputs cannot be negative.")
    daily_demand = demand / Decimal("30")
    coverage_days = stock / daily_demand if daily_demand > 0 else Decimal("Infinity")
    lead_demand = daily_demand * lead_days
    uncovered = max(Decimal("0"), lead_demand - stock)
    holding_total = quantity * holding
    stockout_exposure = uncovered * stockout_cost
    purchase_cash = quantity * unit_cost
    constraints = [
        _constraint("PROCUREMENT_REORDER", "Order quantity restores stock above the reorder point",
                    stock + quantity >= reorder, reorder, stock + quantity,
                    "The submitted order is compared with the stated reorder threshold."),
        _constraint("PROCUREMENT_CASH", "Purchase amount is non-negative", purchase_cash >= 0, 0, purchase_cash,
                    "Purchase amount uses the stated unit cost and order quantity."),
    ]
    score = Decimal("100") if constraints[0].passed else Decimal("0")
    metrics = {"purchase_cash": _result_round(purchase_cash, 2),
               "coverage_days_before_order": _result_round(coverage_days, 1) if coverage_days.is_finite() else None,
               "holding_cost_monthly": _result_round(holding_total, 2),
               "stockout_exposure": _result_round(stockout_exposure, 2),
               "uncovered_lead_time_demand": _result_round(uncovered, 2)}
    alt = DecisionAlternativeEvaluation(
        "ORDER", "Place stated order", DecisionOutcome.FEASIBLE if constraints[0].passed else DecisionOutcome.CONDITIONALLY_FEASIBLE,
        1, float(score), metrics, constraints,
        "Stock coverage, lead-time demand, holding cost, and exposure use only supplied inventory assumptions.",
    )
    return _result("INVENTORY_PROCUREMENT", "Evaluate the stated inventory order quantity.",
                   inputs, metrics, constraints, [alt], alt.explanation, alt.alternative_id)


def evaluate_customer_credit_risk(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    receivable = _decimal(inputs["current_receivable"])
    limit = _decimal(inputs["credit_limit"])
    requested_sale = _decimal(inputs["requested_sale_amount"])
    monthly_sales = _decimal(inputs["average_monthly_sales"])
    margin = _decimal(inputs["gross_margin_pct"])
    default_pct = _decimal(inputs["default_risk_pct"])
    capital_pct = _decimal(inputs["annual_cost_of_capital_pct"])
    terms = _decimal(inputs["proposed_terms_days"])
    overdue = _decimal(inputs["overdue_days"])
    if not 0 <= margin <= 100 or not 0 <= default_pct <= 100 or capital_pct < 0:
        raise ValueError("Credit margin and default risk must be 0–100%; capital cost cannot be negative.")
    post_sale = receivable + requested_sale
    utilization = post_sale / limit * _HUNDRED if limit > 0 else Decimal("Infinity")
    expected_margin = requested_sale * margin / _HUNDRED
    expected_loss = requested_sale * default_pct / _HUNDRED
    funding_cost = requested_sale * capital_pct / _HUNDRED * terms / Decimal("365")
    risk_adjusted_contribution = expected_margin - expected_loss - funding_cost
    constraints = [
        _constraint("CREDIT_LIMIT", "Post-sale receivable is within credit limit", post_sale <= limit, limit, post_sale,
                    "A request above the stated limit is blocked."),
        _constraint("CREDIT_NOT_OVERDUE", "Customer has no overdue exposure", overdue <= 0, 0, overdue,
                    "Existing overdue days are a material collection risk."),
        _constraint("CREDIT_VALUE", "Risk-adjusted contribution is non-negative", risk_adjusted_contribution >= 0, 0, risk_adjusted_contribution,
                    "Expected margin is reduced by expected credit loss and funding cost."),
    ]
    outcome = DecisionOutcome.FEASIBLE if all(item.passed for item in constraints) else DecisionOutcome.NOT_FEASIBLE
    metrics = {"post_sale_receivable": _result_round(post_sale, 2),
               "credit_utilization_pct": _result_round(utilization, 2) if utilization.is_finite() else None,
               "expected_margin": _result_round(expected_margin, 2), "expected_credit_loss": _result_round(expected_loss, 2),
               "funding_cost": _result_round(funding_cost, 2), "risk_adjusted_contribution": _result_round(risk_adjusted_contribution, 2),
               "average_monthly_sales": _result_round(monthly_sales, 2)}
    alt = DecisionAlternativeEvaluation(
        "EXTEND_CREDIT", "Extend the requested credit", outcome, 1,
        80.0 if outcome == DecisionOutcome.FEASIBLE else 25.0, metrics, constraints,
        "The recommendation compares expected contribution with stated default, funding, and overdue exposure.",
    )
    return _result("CUSTOMER_CREDIT_RISK", f"Assess requested credit for {inputs.get('customer_name', 'customer')}.",
                   inputs, metrics, constraints, [alt], alt.explanation,
                   alt.alternative_id if outcome == DecisionOutcome.FEASIBLE else None)


def evaluate_cost_reduction(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    current = _decimal(inputs["current_monthly_cost"])
    proposed = _decimal(inputs["proposed_monthly_cost"])
    implementation = _decimal(inputs["one_time_implementation_cost"])
    quality_cost = _decimal(inputs["expected_quality_cost_monthly"])
    months = int(_decimal(inputs["evaluation_months"]))
    if months <= 0:
        raise ValueError("Evaluation horizon must be greater than zero.")
    monthly_savings = current - proposed - quality_cost
    net_benefit = monthly_savings * months - implementation
    payback = implementation / monthly_savings if monthly_savings > 0 else Decimal("Infinity")
    constraints = [
        _constraint("COST_REDUCTION_SAVINGS", "Recurring net savings are positive", monthly_savings > 0, 0, monthly_savings,
                    "Quality-related recurring cost is deducted from proposed savings.", comparison=">"),
        _constraint("COST_REDUCTION_BENEFIT", "Cumulative benefit exceeds implementation cost", net_benefit > 0, 0, net_benefit,
                    "Benefit is evaluated across the user-stated time horizon.", comparison=">"),
    ]
    outcome = DecisionOutcome.FEASIBLE if all(item.passed for item in constraints) else DecisionOutcome.NOT_FEASIBLE
    metrics = {"monthly_net_savings": _result_round(monthly_savings, 2),
               "net_benefit_over_horizon": _result_round(net_benefit, 2),
               "payback_months": _result_round(payback, 1) if payback.is_finite() else None,
               "evaluation_months": months}
    alt = DecisionAlternativeEvaluation(
        "IMPLEMENT", "Implement the cost reduction", outcome, 1,
        80.0 if outcome == DecisionOutcome.FEASIBLE else 20.0, metrics, constraints,
        "Savings include estimated recurring quality cost and the one-time implementation cost.",
    )
    return _result("COST_REDUCTION", f"Evaluate cost reduction in {inputs.get('cost_category', 'the stated category')}.",
                   inputs, metrics, constraints, [alt], alt.explanation,
                   alt.alternative_id if outcome == DecisionOutcome.FEASIBLE else None)


def evaluate_cash_flow_pressure(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    cash = _decimal(inputs["cash_balance"])
    inflows = _decimal(inputs["monthly_cash_inflows"])
    outflows = _decimal(inputs["monthly_cash_outflows"])
    receivables = _decimal(inputs["receivables_due_30d"])
    collections = _decimal(inputs["receivables_collectible_amount"])
    payables = _decimal(inputs["payables_due_30d"])
    deferral = _decimal(inputs["payables_deferral_amount"])
    line_available = _decimal(inputs["credit_line_available"])
    draw = _decimal(inputs["credit_line_draw_amount"])
    interest = _decimal(inputs["credit_line_interest_pct"])
    survival_floor = _decimal(inputs["monthly_survival_threshold"])
    if interest < 0 or any(value < 0 for value in (cash, inflows, outflows, receivables, collections, payables, deferral, line_available, draw, survival_floor)):
        raise ValueError("Liquidity amounts must be non-negative and credit interest cannot be negative.")
    collections = min(collections, receivables)
    deferral = min(deferral, payables)
    draw = min(draw, line_available)
    base_cash = cash + inflows - outflows - payables
    collection_cash = base_cash + collections
    deferral_cash = base_cash + deferral
    credit_cost = draw * interest / _HUNDRED / Decimal("12")
    credit_cash = base_cash + draw - credit_cost
    cases = [
        ("BASE", "Current schedule", base_cash), ("COLLECT", "Accelerate stated collections", collection_cash),
        ("DEFER", "Defer stated payables", deferral_cash), ("CREDIT", "Draw stated credit line", credit_cash),
    ]
    raw_collections = _decimal(inputs["receivables_collectible_amount"])
    raw_deferral = _decimal(inputs["payables_deferral_amount"])
    raw_draw = _decimal(inputs["credit_line_draw_amount"])
    collections = min(raw_collections, receivables)
    deferral = min(raw_deferral, payables)
    draw = min(raw_draw, line_available)
    constraints = [
        _constraint("LIQUIDITY_COLLECTION_LIMIT", "Accelerated collection does not exceed receivables", raw_collections <= receivables, receivables, raw_collections,
                    "Collections are capped by stated receivables."),
        _constraint("LIQUIDITY_PAYABLE_LIMIT", "Payable deferral does not exceed due payables", raw_deferral <= payables, payables, raw_deferral,
                    "Deferral is capped by stated due payables."),
        _constraint("LIQUIDITY_CREDIT_LIMIT", "Credit draw does not exceed facility", raw_draw <= line_available, line_available, raw_draw,
                    "Facility draw is capped by available credit."),
    ]
    alternatives = []
    for rank, (identifier, label, projected) in enumerate(cases, 1):
        feasible = projected >= survival_floor
        alternatives.append(DecisionAlternativeEvaluation(
            identifier, label, DecisionOutcome.FEASIBLE if feasible else DecisionOutcome.NOT_FEASIBLE,
            rank, float(max(Decimal("0"), min(_HUNDRED, projected / max(survival_floor, Decimal("1")) * _HUNDRED))),
            {"projected_30d_cash": _result_round(projected, 2), "survival_threshold": _result_round(survival_floor, 2),
             "credit_interest_cost": _result_round(credit_cost if identifier == "CREDIT" else Decimal("0"), 2)},
            constraints, f"Projected 30-day cash under this explicitly quantified response is {projected:.2f}.",
        ))
    best = max(alternatives, key=lambda item: Decimal(str(item.metrics["projected_30d_cash"])))
    calculations = {"base_projected_30d_cash": _result_round(base_cash, 2),
                    "best_case_projected_30d_cash": _result_round(Decimal(str(best.metrics["projected_30d_cash"])), 2)}
    feasible = best.metrics["projected_30d_cash"] >= best.metrics["survival_threshold"]
    nodes, edges = _graph(inputs, calculations, DecisionOutcome.FEASIBLE.value if feasible else DecisionOutcome.NOT_FEASIBLE.value)
    return DecisionEvaluationResult("CASH_FLOW_PRESSURE", "1.0.0",
        "Assess short-term cash pressure and stated response options.", inputs, calculations, constraints,
        DecisionOutcome.FEASIBLE if feasible else DecisionOutcome.NOT_FEASIBLE, best.explanation,
        best.alternative_id if feasible else None, alternatives, nodes, edges)


def evaluate_business_viability(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    revenue = _decimal(inputs["current_monthly_revenue"])
    variable_pct = _decimal(inputs["variable_cost_pct"])
    fixed = _decimal(inputs["monthly_fixed_costs"])
    cash = _decimal(inputs["cash_balance"])
    debt_service = _decimal(inputs["monthly_debt_service"])
    working_capital = _decimal(inputs["current_working_capital"])
    growth_pct = _decimal(inputs["monthly_revenue_growth_pct"])
    interest_pct = _decimal(inputs["annual_interest_rate_pct"])
    capex = _decimal(inputs["monthly_capex"])
    current_debt = _decimal(inputs["current_debt"])
    if not 0 <= variable_pct <= 100 or growth_pct <= -100 or interest_pct < 0:
        raise ValueError("Variable cost must be 0–100%, growth must be above -100%, and interest cannot be negative.")
    contribution_ratio = (_HUNDRED - variable_pct) / _HUNDRED
    break_even_revenue = fixed / contribution_ratio if contribution_ratio > 0 else Decimal("Infinity")
    month_cash = cash
    minimum_cash = cash
    total_operating = Decimal("0")
    for month in range(1, 13):
        projected_revenue = revenue * ((_ONE + growth_pct / _HUNDRED) ** month)
        operating = projected_revenue * contribution_ratio - fixed - debt_service - capex
        total_operating += operating
        month_cash += operating
        minimum_cash = min(minimum_cash, month_cash)
    dscr = (revenue * contribution_ratio - fixed) / debt_service if debt_service > 0 else Decimal("Infinity")
    constraints = [
        _constraint("VIABILITY_BREAK_EVEN", "Current revenue covers fixed cost at contribution margin", revenue >= break_even_revenue,
                    break_even_revenue if break_even_revenue.is_finite() else None, revenue,
                    "Break-even revenue uses stated fixed cost and variable cost percentage."),
        _constraint("VIABILITY_CASH", "Projected minimum cash remains non-negative for 12 months", minimum_cash >= 0 and working_capital >= 0,
                    0, minimum_cash, "Cash projection uses stated revenue growth, debt service, fixed costs, and capex."),
        _constraint("VIABILITY_DSCR", "Debt service coverage is at least 1.0x", debt_service == 0 or dscr >= 1,
                    1, dscr if dscr.is_finite() else None, "Coverage excludes financing not included in stated monthly debt service."),
    ]
    calculations = {
        "contribution_margin_ratio_pct": _result_round(contribution_ratio * _HUNDRED, 2),
        "break_even_monthly_revenue": _result_round(break_even_revenue, 2) if break_even_revenue.is_finite() else None,
        "twelve_month_operating_cash_change": _result_round(total_operating, 2),
        "minimum_projected_cash": _result_round(minimum_cash, 2),
        "ending_projected_cash": _result_round(month_cash, 2),
        "debt_service_coverage_ratio": _result_round(dscr, 2) if dscr.is_finite() else None,
        "current_debt": _result_round(current_debt, 2), "annual_interest_rate_pct": _result_round(interest_pct, 2),
    }
    outcome = DecisionOutcome.FEASIBLE if all(item.passed for item in constraints) else DecisionOutcome.NOT_FEASIBLE
    alt = DecisionAlternativeEvaluation("CONTINUE", "Continue on stated 12-month plan", outcome, 1,
                                        85.0 if outcome == DecisionOutcome.FEASIBLE else 20.0,
                                        calculations, constraints,
                                        "12-month outlook uses the submitted unit economics, growth, debt service, working capital, and capex.")
    return _result("BUSINESS_VIABILITY", "Assess structural unit economics and 12-month solvency.",
                   inputs, calculations, constraints, [alt], alt.explanation,
                   alt.alternative_id if outcome == DecisionOutcome.FEASIBLE else None)


def evaluate_location_selection(inputs: dict[str, Any], constraints_override=None) -> DecisionEvaluationResult:
    candidates = inputs["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("At least one explicitly evidenced location candidate is required.")
    candidate_results = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError("Every location candidate must be an object.")
        name = str(candidate.get("location_name", f"Candidate {index + 1}"))
        capex = _decimal(candidate["fitout_capex"])
        rent = _decimal(candidate["monthly_rent"])
        staff = _decimal(candidate["monthly_staff_cost"])
        demand = _decimal(candidate["catchment_monthly_demand"])
        conversion_pct = _decimal(candidate["conversion_rate_pct"])
        order_value = _decimal(candidate["average_order_value"])
        margin_pct = _decimal(candidate["gross_margin_pct"])
        cannibalization = _decimal(candidate["cannibalization_pct"])
        if not 0 <= conversion_pct <= 100 or not 0 <= margin_pct <= 100 or not 0 <= cannibalization <= 100:
            raise ValueError(f"Location candidate {name} has a percentage outside 0–100.")
        expected_sales = demand * conversion_pct / _HUNDRED * order_value * (_ONE - cannibalization / _HUNDRED)
        contribution = expected_sales * margin_pct / _HUNDRED - rent - staff
        payback = capex / contribution if contribution > 0 else Decimal("Infinity")
        kpis = _compute_alternative_kpis(capex, contribution, contribution, 0)
        metrics = {
            "expected_monthly_sales": _result_round(expected_sales, 2),
            "monthly_net_contribution": _result_round(contribution, 2),
            "monthly_net_cash_impact": _result_round(contribution, 2),
            "net_monthly_cash_flow": _result_round(contribution, 2),
            "fitout_payback_months": _result_round(payback, 1) if payback.is_finite() else None,
            "payback_months": kpis["payback_period_months"],
            "payback_period_months": kpis["payback_period_months"],
            "fitout_capex": _result_round(capex, 2),
            "monthly_rent": _result_round(rent, 2),
            "npv_amount": kpis["npv_amount"],
            "npv": kpis["npv_amount"],
            "roi_pct": kpis["roi_pct"],
            "irr_pct": kpis["irr_pct"],
        }
        candidate_results.append((index, name, metrics, contribution > 0))
    ranked = sorted(candidate_results, key=lambda item: Decimal(str(item[2]["monthly_net_contribution"])), reverse=True)
    alternatives = []
    for rank, (index, name, metrics, passed) in enumerate(ranked, 1):
        constraints = [_constraint(f"LOCATION_CONTRIBUTION_{index}", "Monthly contribution after rent and staff is positive",
                                  passed, 0, metrics["monthly_net_contribution"],
                                  "Demand, conversion, average order value, margin, rent, staff, and cannibalization come from candidate inputs.",
                                  comparison=">")]
        contribution = Decimal(str(metrics["monthly_net_contribution"]))
        score = max(Decimal("0"), min(_HUNDRED, contribution / max(Decimal("1"), abs(contribution)) * _HUNDRED))
        alternatives.append(DecisionAlternativeEvaluation(
            f"LOCATION_{index + 1}", name, DecisionOutcome.FEASIBLE if passed else DecisionOutcome.NOT_FEASIBLE,
            rank, float(score), metrics, constraints,
            f"Expected contribution after stated rent and staff cost: {metrics['monthly_net_contribution']:.2f}.",
        ))
    recommended = alternatives[0].alternative_id if alternatives and alternatives[0].outcome == DecisionOutcome.FEASIBLE else None
    outcome = DecisionOutcome.FEASIBLE if recommended else DecisionOutcome.NOT_FEASIBLE
    calculation = {"candidate_count": len(alternatives)}
    nodes, edges = _graph(inputs, calculation, outcome.value)
    return DecisionEvaluationResult("LOCATION_SELECTION", "1.0.0",
        "Compare locations from user or evidence supplied site assumptions.", inputs, calculation,
        [c for a in alternatives for c in a.constraints], outcome,
        "Candidates rank by expected monthly contribution; no geographic defaults are used.",
        recommended, alternatives, nodes, edges)
