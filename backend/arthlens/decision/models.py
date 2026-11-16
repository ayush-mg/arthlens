"""
Versioned Decision Models & Typed Decision Graph.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 4: Decision Intelligence Engine (8 Versioned Models, Typed Graph, Constraint Evaluation).
"""

from __future__ import annotations

from builtins import round as _builtin_round
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import uuid

from backend.arthlens.domain.business import DecisionOutcome, Money
_ZERO = Decimal("0")
_ONE = Decimal("1")
_HUNDRED = Decimal("100")
_TWELVE = Decimal("12")
_THIRTY = Decimal("30")


def _decimal(value: Any, default: Any = "0") -> Decimal:
    """Parse financial inputs without converting through binary floating point."""
    if value is None:
        value = default
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Expected a finite numeric decision input, received {value!r}.") from exc
    if not number.is_finite():
        raise ValueError("Decision inputs must be finite numbers.")
    return number


def _result_round(value: Any, ndigits: int = 0) -> float:
    """Round an internal Decimal and convert it to a JSON-safe number at output."""
    if isinstance(value, Decimal):
        quantum = Decimal("1").scaleb(-ndigits)
        return float(value.quantize(quantum, rounding=ROUND_HALF_UP))
    return _builtin_round(value, ndigits)


def _json_safe(value: Any) -> Any:
    """Convert Decimal values recursively at the API and persistence boundary."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _monthly_installment(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    """Calculate an installment with Decimal arithmetic and an explicit integer term."""
    if principal <= _ZERO:
        return _ZERO
    if months <= 0:
        raise ValueError("Loan tenure must be a positive integer.")
    if annual_rate < _ZERO:
        raise ValueError("Loan interest rate must be non-negative.")
    with localcontext() as context:
        context.prec = 40
        monthly_rate = annual_rate / _TWELVE
        if monthly_rate == _ZERO:
            return principal / Decimal(months)
        factor = (_ONE + monthly_rate) ** months
        return principal * monthly_rate * factor / (factor - _ONE)


def _compute_alternative_kpis(
    initial_outflow: Decimal,
    monthly_cf_during: Decimal,
    monthly_cf_post: Decimal,
    loan_tenure_months: int,
    total_months: int = 60,
    annual_discount_rate: Decimal = Decimal("0.12"),
) -> Dict[str, float]:
    """
    Computes rigorous capital budgeting KPIs: NPV, Payback, ROI %, and IRR %
    across the project lifespan with Decimal arithmetic.
    """
    init_f = max(float(initial_outflow), 0.0)
    during_f = float(monthly_cf_during)
    post_f = float(monthly_cf_post)
    r_m = float(annual_discount_rate) / 12.0

    cfs = [during_f if m <= loan_tenure_months else post_f for m in range(1, total_months + 1)]

    # 1. Net Present Value (NPV)
    npv = -init_f
    for t, cf in enumerate(cfs, 1):
        npv += cf / ((1.0 + r_m) ** t)

    # 2. Payback Period in Months
    cum = 0.0
    payback = 999.0
    if init_f <= 0.0:
        payback = 0.0
    else:
        for t, cf in enumerate(cfs, 1):
            prev = cum
            cum += cf
            if cum >= init_f:
                frac = (init_f - prev) / max(cf, 0.01) if cf > 0 else 0.0
                payback = round((t - 1) + frac, 1)
                break

    # 3. Return on Investment (ROI %)
    total_gain = sum(cfs)
    denom = init_f if init_f > 0 else max(total_gain, 1.0)
    roi_pct = round(((total_gain - init_f) / denom) * 100.0, 1) if init_f > 0 else round((total_gain / max(total_gain + 1000.0, 1.0)) * 100.0, 1)

    # 4. Internal Rate of Return (IRR %)
    def npv_at(rate: float) -> float:
        val = -init_f
        for t, cf in enumerate(cfs, 1):
            val += cf / ((1.0 + rate) ** t)
        return val

    low, high = -0.5, 2.0
    irr_pct = 0.0
    if init_f > 0 and npv_at(low) * npv_at(high) <= 0:
        mid = 0.0
        for _ in range(30):
            mid = (low + high) / 2.0
            if abs(npv_at(mid)) < 1.0:
                break
            if npv_at(low) * npv_at(mid) < 0:
                high = mid
            else:
                low = mid
        irr_pct = round((((1.0 + mid) ** 12) - 1.0) * 100.0, 1)
    else:
        annual_avg_gain = total_gain / (total_months / 12.0)
        irr_pct = round(max((annual_avg_gain / max(init_f, 1.0)) * 100.0, 0.0), 1)

    return {
        "npv_amount": round(npv, 2),
        "payback_period_months": payback,
        "roi_pct": roi_pct,
        "irr_pct": irr_pct,
    }


def _build_comparative_alternatives(
    model_id: str,
    baseline_name: str,
    initial_outflow: Decimal,
    monthly_gain: Decimal,
    base_outcome: DecisionOutcome,
    constraints: List[DecisionConstraintResult],
    score: float = 85.0,
) -> List[DecisionAlternativeEvaluation]:
    """Generates 3 deterministic comparative alternatives with full capital budgeting KPIs."""
    alts = []
    # 1. Base Alternative
    kpi_base = _compute_alternative_kpis(initial_outflow, monthly_gain, monthly_gain, 0)
    alts.append(DecisionAlternativeEvaluation(
        alternative_id=f"ALT_{model_id}_BASE",
        name=f"Primary Strategy: {baseline_name}",
        outcome=base_outcome,
        rank=1,
        score=score if base_outcome == DecisionOutcome.FEASIBLE else 45.0,
        metrics={
            "initial_outflow": _result_round(initial_outflow, 2),
            "monthly_net_gain": _result_round(monthly_gain, 2),
            "monthly_net_cash_impact": _result_round(monthly_gain, 2),
            "net_monthly_cash_flow": _result_round(monthly_gain, 2),
            "payback_months": kpi_base["payback_period_months"],
            "payback_period_months": kpi_base["payback_period_months"],
            "npv_amount": kpi_base["npv_amount"],
            "npv": kpi_base["npv_amount"],
            "roi_pct": kpi_base["roi_pct"],
            "irr_pct": kpi_base["irr_pct"],
        },
        constraints=constraints,
        explanation="Baseline operational parameters submitted for evaluation.",
    ))

    # 2. Conservative Alternative (-20% Gain, +10% Outflow buffer)
    outflow_c = initial_outflow * Decimal("1.10")
    gain_c = monthly_gain * Decimal("0.80")
    kpi_c = _compute_alternative_kpis(outflow_c, gain_c, gain_c, 0)
    alts.append(DecisionAlternativeEvaluation(
        alternative_id=f"ALT_{model_id}_CONSERVATIVE",
        name=f"Conservative Buffer Strategy (-20% return stress)",
        outcome=DecisionOutcome.FEASIBLE if gain_c > _ZERO else DecisionOutcome.NOT_FEASIBLE,
        rank=2,
        score=70.0 if gain_c > _ZERO else 35.0,
        metrics={
            "initial_outflow": _result_round(outflow_c, 2),
            "monthly_net_gain": _result_round(gain_c, 2),
            "monthly_net_cash_impact": _result_round(gain_c, 2),
            "net_monthly_cash_flow": _result_round(gain_c, 2),
            "payback_months": kpi_c["payback_period_months"],
            "payback_period_months": kpi_c["payback_period_months"],
            "npv_amount": kpi_c["npv_amount"],
            "npv": kpi_c["npv_amount"],
            "roi_pct": kpi_c["roi_pct"],
            "irr_pct": kpi_c["irr_pct"],
        },
        constraints=constraints,
        explanation="Downside stress test simulating conservative operational returns.",
    ))

    # 3. Phased / Lean Implementation (50% scale)
    outflow_p = initial_outflow * Decimal("0.50")
    gain_p = monthly_gain * Decimal("0.55")
    kpi_p = _compute_alternative_kpis(outflow_p, gain_p, gain_p, 0)
    alts.append(DecisionAlternativeEvaluation(
        alternative_id=f"ALT_{model_id}_PHASED",
        name=f"Phased Deployment Strategy (50% initial commitment)",
        outcome=DecisionOutcome.FEASIBLE if gain_p > _ZERO else DecisionOutcome.NOT_FEASIBLE,
        rank=3,
        score=65.0 if gain_p > _ZERO else 30.0,
        metrics={
            "initial_outflow": _result_round(outflow_p, 2),
            "monthly_net_gain": _result_round(gain_p, 2),
            "monthly_net_cash_impact": _result_round(gain_p, 2),
            "net_monthly_cash_flow": _result_round(gain_p, 2),
            "payback_months": kpi_p["payback_period_months"],
            "payback_period_months": kpi_p["payback_period_months"],
            "npv_amount": kpi_p["npv_amount"],
            "npv": kpi_p["npv_amount"],
            "roi_pct": kpi_p["roi_pct"],
            "irr_pct": kpi_p["irr_pct"],
        },
        constraints=constraints,
        explanation="Staged rollout limiting upfront working capital drainage.",
    ))
    return alts


# ==============================================================================
# 1. Graph Node Types & Typed Graph Structures
# ==============================================================================

class DecisionNodeType(str, Enum):
    INPUT = "INPUT"
    ASSUMPTION = "ASSUMPTION"
    CONSTRAINT = "CONSTRAINT"
    CALCULATION = "CALCULATION"
    OUTCOME = "OUTCOME"


@dataclass(frozen=True)
class DecisionGraphNode:
    id: str
    label: str
    node_type: DecisionNodeType
    value: Any
    description: str = ""
    unit: str = ""


@dataclass(frozen=True)
class DecisionGraphEdge:
    source_id: str
    target_id: str
    relation: str = "DERIVED_FROM"


@dataclass(frozen=True)
class DecisionConstraintResult:
    constraint_id: str
    label: str
    is_hard_constraint: bool
    passed: bool
    threshold_value: Any
    actual_value: Any
    comparison: str  # >=, <=, ==, >
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe({
            "constraint_id": self.constraint_id,
            "label": self.label,
            "is_hard_constraint": self.is_hard_constraint,
            "passed": self.passed,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "comparison": self.comparison,
            "explanation": self.explanation,
        })


@dataclass(frozen=True)
class DecisionAlternativeEvaluation:
    alternative_id: str
    name: str
    outcome: DecisionOutcome
    rank: int
    score: float  # 0 to 100
    metrics: Dict[str, Any]
    constraints: List[DecisionConstraintResult]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe({
            "alternative_id": self.alternative_id,
            "name": self.name,
            "outcome": self.outcome.value,
            "rank": self.rank,
            "score": self.score,
            "metrics": self.metrics,
            "constraints": [c.to_dict() for c in self.constraints],
            "explanation": self.explanation,
        })


@dataclass(frozen=True)
class DecisionEvaluationResult:
    model_id: str
    model_version: str
    objective: str
    inputs: Dict[str, Any]
    calculations: Dict[str, Any]
    constraints: List[DecisionConstraintResult]
    outcome: DecisionOutcome
    summary_explanation: str
    recommended_alternative: Optional[str] = None
    alternatives: List[DecisionAlternativeEvaluation] = field(default_factory=list)
    graph_nodes: List[DecisionGraphNode] = field(default_factory=list)
    graph_edges: List[DecisionGraphEdge] = field(default_factory=list)
    evaluation_id: Optional[str] = None
    version_number: Optional[int] = None
    parent_decision_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe({
            "model_id": self.model_id,
            "model_version": self.model_version,
            "objective": self.objective,
            "outcome": self.outcome.value,
            "summary_explanation": self.summary_explanation,
            "recommended_alternative": self.recommended_alternative,
            "inputs": self.inputs,
            "calculations": self.calculations,
            "constraints": [c.to_dict() for c in self.constraints],
            "alternatives": [a.to_dict() for a in self.alternatives],
            "graph": {
                "nodes": [
                    {
                        "id": n.id,
                        "label": n.label,
                        "type": n.node_type.value,
                        "value": n.value,
                        "unit": n.unit,
                        "description": n.description,
                    }
                    for n in self.graph_nodes
                ],
                "edges": [
                    {
                        "source": e.source_id,
                        "target": e.target_id,
                        "relation": e.relation,
                    }
                    for e in self.graph_edges
                ],
            },
            "evaluation_id": self.evaluation_id,
            "version_number": self.version_number,
            "parent_decision_id": self.parent_decision_id,
        })


# ==============================================================================
# 2. Model 1: NEW_PRODUCT_ADDITION (v1.0.0)
# ==============================================================================

def evaluate_new_product_addition(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """Evaluates launch of a new product considering contribution margin, break-even volume, and payback."""
    name = str(inputs.get("product_name", "New Product"))
    selling_price = _decimal(inputs.get("selling_price", 0.0))
    variable_cost = _decimal(inputs.get("variable_cost", 0.0))
    expected_monthly_volume = _decimal(inputs.get("expected_monthly_volume", 0.0))
    setup_cost = _decimal(inputs.get("setup_cost", 0.0))
    cannibalization_rate = _decimal(inputs.get("cannibalization_rate", 0.0))

    if selling_price <= _ZERO or expected_monthly_volume <= _ZERO:
        return DecisionEvaluationResult(
            model_id="NEW_PRODUCT_ADDITION",
            model_version="1.0.0",
            objective=f"Evaluate feasibility of introducing {name}",
            inputs=inputs,
            calculations={},
            constraints=[],
            outcome=DecisionOutcome.INSUFFICIENT_INFORMATION,
            summary_explanation="Selling price and monthly volume must be positive non-zero values.",
        )

    unit_margin = selling_price - variable_cost
    margin_pct = (unit_margin / selling_price) * _HUNDRED if selling_price > _ZERO else _ZERO
    effective_volume = expected_monthly_volume * (_ONE - cannibalization_rate)
    monthly_gross_contribution = effective_volume * unit_margin
    annual_contribution = monthly_gross_contribution * _TWELVE
    payback_months = (setup_cost / monthly_gross_contribution) if monthly_gross_contribution > _ZERO else Decimal("999")
    break_even_units = (setup_cost / unit_margin) if unit_margin > _ZERO else Decimal("999999")

    calculations = {
        "unit_contribution_margin": _result_round(unit_margin, 2),
        "contribution_margin_percent": _result_round(margin_pct, 2),
        "effective_monthly_volume": _result_round(effective_volume, 1),
        "monthly_gross_contribution": _result_round(monthly_gross_contribution, 2),
        "annual_gross_contribution": _result_round(annual_contribution, 2),
        "payback_period_months": _result_round(payback_months, 1),
        "break_even_units_to_recoup_setup": _result_round(break_even_units, 0),
    }

    # Constraints
    c_list: List[DecisionConstraintResult] = []
    # 1. Positive unit margin (Hard)
    passed_m = unit_margin > _ZERO
    c_list.append(DecisionConstraintResult(
        constraint_id="POSITIVE_UNIT_MARGIN",
        label="Unit Contribution Margin Must Be Positive",
        is_hard_constraint=True,
        passed=passed_m,
        threshold_value=0.0,
        actual_value=_result_round(unit_margin, 2),
        comparison=">",
        explanation="Product must generate positive cash above variable cost on every unit sold."
        if passed_m else "Selling price is below variable production cost.",
    ))

    # 2. Payback period <= 18 months (Hard)
    max_payback = _decimal((constraints_override or {}).get("max_payback_months", 18.0))
    passed_pb = payback_months <= max_payback
    c_list.append(DecisionConstraintResult(
        constraint_id="PAYBACK_PERIOD",
        label=f"Setup Cost Payback Within {max_payback:.0f} Months",
        is_hard_constraint=True,
        passed=passed_pb,
        threshold_value=_result_round(max_payback, 1),
        actual_value=_result_round(payback_months, 1),
        comparison="<=",
        explanation=f"Setup cost recouped in {payback_months:.1f} months, well within {max_payback:.0f} month threshold."
        if passed_pb else f"Payback period of {payback_months:.1f} months exceeds maximum allowable duration.",
    ))

    # 3. Minimum margin % >= 20% (Soft)
    min_margin = _decimal((constraints_override or {}).get("min_margin_percent", 20.0))
    passed_mp = margin_pct >= min_margin
    c_list.append(DecisionConstraintResult(
        constraint_id="MINIMUM_MARGIN_PERCENT",
        label=f"Contribution Margin At Least {min_margin:.0f}%",
        is_hard_constraint=False,
        passed=passed_mp,
        threshold_value=_result_round(min_margin, 1),
        actual_value=_result_round(margin_pct, 2),
        comparison=">=",
        explanation=f"Healthy contribution margin of {margin_pct:.1f}%."
        if passed_mp else f"Margin ({margin_pct:.1f}%) is thinner than target {min_margin:.0f}%.",
    ))

    hard_passed = all(c.passed for c in c_list if c.is_hard_constraint)
    all_passed = all(c.passed for c in c_list)

    if all_passed:
        outcome = DecisionOutcome.FEASIBLE
        summary = f"Introducing {name} is FEASIBLE. Generates ₹{monthly_gross_contribution:,.0f}/month with a {payback_months:.1f}-month setup payback."
    elif hard_passed:
        outcome = DecisionOutcome.CONDITIONALLY_FEASIBLE
        summary = f"Introducing {name} is CONDITIONALLY FEASIBLE. Viable but margin ({margin_pct:.1f}%) requires strict cost control."
    else:
        outcome = DecisionOutcome.NOT_FEASIBLE
        failed_names = [c.label for c in c_list if c.is_hard_constraint and not c.passed]
        summary = f"Introducing {name} is NOT FEASIBLE. Failed critical constraints: {', '.join(failed_names)}."

    # Build 3 Comparative Strategic Alternatives
    alt_list: List[DecisionAlternativeEvaluation] = []
    kpi_base = _compute_alternative_kpis(setup_cost, monthly_gross_contribution, monthly_gross_contribution, 0)
    alt_list.append(DecisionAlternativeEvaluation(
        alternative_id="ALT_PROD_BASE",
        name=f"Standard Product Launch ({expected_monthly_volume:,.0f} units @ ₹{selling_price:,.2f})",
        outcome=outcome,
        rank=1 if all_passed else 2,
        score=85.0 if all_passed else (60.0 if hard_passed else 35.0),
        metrics={
            "setup_cost": _result_round(setup_cost, 2),
            "monthly_gross_contribution": _result_round(monthly_gross_contribution, 2),
            "monthly_net_cash_impact": _result_round(monthly_gross_contribution, 2),
            "net_monthly_cash_flow": _result_round(monthly_gross_contribution, 2),
            "payback_months": kpi_base["payback_period_months"],
            "payback_period_months": kpi_base["payback_period_months"],
            "npv_amount": kpi_base["npv_amount"],
            "npv": kpi_base["npv_amount"],
            "roi_pct": kpi_base["roi_pct"],
            "irr_pct": kpi_base["irr_pct"],
        },
        constraints=c_list,
        explanation="Standard commercial launch targeting full expected catchment volume.",
    ))

    vol_c = expected_monthly_volume * Decimal("0.8")
    contrib_c = vol_c * unit_margin
    kpi_c = _compute_alternative_kpis(setup_cost, contrib_c, contrib_c, 0)
    alt_list.append(DecisionAlternativeEvaluation(
        alternative_id="ALT_PROD_CONSERVATIVE",
        name=f"Conservative Ramp-Up ({vol_c:,.0f} units @ ₹{selling_price:,.2f})",
        outcome=DecisionOutcome.FEASIBLE if contrib_c > _ZERO else DecisionOutcome.NOT_FEASIBLE,
        rank=2 if all_passed else 1,
        score=75.0 if contrib_c > _ZERO else 40.0,
        metrics={
            "setup_cost": _result_round(setup_cost, 2),
            "monthly_gross_contribution": _result_round(contrib_c, 2),
            "monthly_net_cash_impact": _result_round(contrib_c, 2),
            "net_monthly_cash_flow": _result_round(contrib_c, 2),
            "payback_months": kpi_c["payback_period_months"],
            "payback_period_months": kpi_c["payback_period_months"],
            "npv_amount": kpi_c["npv_amount"],
            "npv": kpi_c["npv_amount"],
            "roi_pct": kpi_c["roi_pct"],
            "irr_pct": kpi_c["irr_pct"],
        },
        constraints=c_list,
        explanation="Stress-tests product viability under 20% lower initial customer adoption.",
    ))

    p_prem = selling_price * Decimal("1.15")
    vol_prem = expected_monthly_volume * Decimal("0.9")
    contrib_prem = vol_prem * (p_prem - variable_cost)
    kpi_p = _compute_alternative_kpis(setup_cost, contrib_prem, contrib_prem, 0)
    alt_list.append(DecisionAlternativeEvaluation(
        alternative_id="ALT_PROD_PREMIUM",
        name=f"Premium Positioning ({vol_prem:,.0f} units @ ₹{p_prem:,.2f})",
        outcome=DecisionOutcome.FEASIBLE if contrib_prem > _ZERO else DecisionOutcome.NOT_FEASIBLE,
        rank=3,
        score=80.0 if contrib_prem > _ZERO else 45.0,
        metrics={
            "setup_cost": _result_round(setup_cost, 2),
            "monthly_gross_contribution": _result_round(contrib_prem, 2),
            "monthly_net_cash_impact": _result_round(contrib_prem, 2),
            "net_monthly_cash_flow": _result_round(contrib_prem, 2),
            "payback_months": kpi_p["payback_period_months"],
            "payback_period_months": kpi_p["payback_period_months"],
            "npv_amount": kpi_p["npv_amount"],
            "npv": kpi_p["npv_amount"],
            "roi_pct": kpi_p["roi_pct"],
            "irr_pct": kpi_p["irr_pct"],
        },
        constraints=c_list,
        explanation="Captures higher margin per unit with slightly lower initial volume.",
    ))

    # Build Graph
    nodes = [
        DecisionGraphNode("in_price", f"Selling Price: ₹{selling_price}", DecisionNodeType.INPUT, selling_price, "Unit Price", "INR"),
        DecisionGraphNode("in_cost", f"Variable Cost: ₹{variable_cost}", DecisionNodeType.INPUT, variable_cost, "Unit Variable Cost", "INR"),
        DecisionGraphNode("in_vol", f"Expected Vol: {expected_monthly_volume}", DecisionNodeType.INPUT, expected_monthly_volume, "Monthly Units", "pcs"),
        DecisionGraphNode("calc_margin", f"Unit Margin: ₹{unit_margin:.2f}", DecisionNodeType.CALCULATION, unit_margin, "Contribution Margin", "INR"),
        DecisionGraphNode("calc_profit", f"Monthly Gross: ₹{monthly_gross_contribution:.2f}", DecisionNodeType.CALCULATION, monthly_gross_contribution, "Monthly Gross Contribution", "INR"),
        DecisionGraphNode("calc_payback", f"Payback: {payback_months:.1f} mos", DecisionNodeType.CALCULATION, payback_months, "Payback Period", "months"),
        DecisionGraphNode("out_res", f"Outcome: {outcome.value}", DecisionNodeType.OUTCOME, outcome.value, summary),
    ]
    edges = [
        DecisionGraphEdge("in_price", "calc_margin"),
        DecisionGraphEdge("in_cost", "calc_margin"),
        DecisionGraphEdge("calc_margin", "calc_profit"),
        DecisionGraphEdge("in_vol", "calc_profit"),
        DecisionGraphEdge("calc_profit", "calc_payback"),
        DecisionGraphEdge("calc_payback", "out_res"),
    ]

    return DecisionEvaluationResult(
        model_id="NEW_PRODUCT_ADDITION",
        model_version="1.0.0",
        objective=f"Evaluate feasibility of introducing {name}",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        graph_nodes=nodes,
        graph_edges=edges,
        alternatives=alt_list,
    )


# ==============================================================================
# 3. Model 2: MACHINE_OR_EQUIPMENT_PURCHASE (v1.0.0) - Flagship ₹8 Lakh Journey
# ==============================================================================

def evaluate_equipment_purchase(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """
    Evaluates equipment/machinery procurement with financing alternatives,
    incremental throughput, DSCR coverage, cash runway floor, and payback.
    """
    required_inputs = (
        "machine_cost",
        "down_payment",
        "loan_interest_rate_pct",
        "loan_tenure_months",
        "monthly_maintenance",
        "current_monthly_volume",
        "capacity_monthly_volume",
        "unit_price",
        "unit_variable_cost",
        "current_cash_liquidity",
        "current_monthly_ebitda",
    )
    missing_inputs = [key for key in required_inputs if inputs.get(key) is None]
    if missing_inputs:
        return DecisionEvaluationResult(
            model_id="MACHINE_OR_EQUIPMENT_PURCHASE",
            model_version="1.0.0",
            objective="Evaluate an equipment purchase using supplied terms and business records",
            inputs={**inputs, "missing_inputs": missing_inputs},
            calculations={},
            constraints=[],
            outcome=DecisionOutcome.INSUFFICIENT_INFORMATION,
            summary_explanation="Missing required decision inputs: " + ", ".join(missing_inputs),
        )

    machine_name = str(inputs.get("machine_name", "Production Equipment"))
    machine_cost = _decimal(inputs["machine_cost"])
    down_payment = _decimal(inputs["down_payment"])
    loan_amount = _decimal(inputs.get("loan_amount", max(_ZERO, machine_cost - down_payment)))
    interest_rate_pct = _decimal(inputs["loan_interest_rate_pct"])
    tenure_months = int(inputs["loan_tenure_months"])
    monthly_maintenance = _decimal(inputs["monthly_maintenance"])

    # Throughput & unit economics are supplied explicitly by the user.
    current_volume = _decimal(inputs["current_monthly_volume"])
    capacity_volume = _decimal(inputs["capacity_monthly_volume"])
    incremental_volume = max(_ZERO, capacity_volume - current_volume)
    unit_price = _decimal(inputs["unit_price"])
    unit_variable_cost = _decimal(inputs["unit_variable_cost"])
    current_cash_liquidity = _decimal(inputs["current_cash_liquidity"])
    current_monthly_ebitda = _decimal(inputs["current_monthly_ebitda"])

    if machine_cost <= _ZERO:
        return DecisionEvaluationResult(
            model_id="MACHINE_OR_EQUIPMENT_PURCHASE",
            model_version="1.0.0",
            objective=f"Evaluate capital purchase of {machine_name}",
            inputs=inputs,
            calculations={},
            constraints=[],
            outcome=DecisionOutcome.INSUFFICIENT_INFORMATION,
            summary_explanation="Machine capital cost must be strictly positive.",
        )

    # 1. Base Alternative: Standard Bank Term Loan
    rate_fraction = interest_rate_pct / _HUNDRED if interest_rate_pct > _ONE else interest_rate_pct
    emi = _monthly_installment(loan_amount, rate_fraction, tenure_months) if loan_amount > _ZERO else _ZERO
    unit_margin = unit_price - unit_variable_cost
    incremental_revenue = incremental_volume * unit_price
    incremental_gross_profit = incremental_volume * unit_margin
    monthly_operating_gain = incremental_gross_profit - monthly_maintenance
    net_monthly_cash_flow = monthly_operating_gain - emi

    total_available_ebitda = current_monthly_ebitda + monthly_operating_gain
    dscr = (total_available_ebitda / emi) if emi > _ZERO else Decimal("999")

    post_purchase_cash = current_cash_liquidity - down_payment
    payback_months = (machine_cost / monthly_operating_gain) if monthly_operating_gain > _ZERO else Decimal("999")

    calculations = {
        "machine_cost": _result_round(machine_cost, 2),
        "down_payment": _result_round(down_payment, 2),
        "loan_principal": _result_round(loan_amount, 2),
        "monthly_emi": _result_round(emi, 2),
        "incremental_monthly_volume": _result_round(incremental_volume, 0),
        "incremental_monthly_revenue": _result_round(incremental_revenue, 2),
        "incremental_monthly_gross_profit": _result_round(incremental_gross_profit, 2),
        "net_monthly_operating_gain": _result_round(monthly_operating_gain, 2),
        "net_monthly_cash_flow_after_emi": _result_round(net_monthly_cash_flow, 2),
        "total_monthly_ebitda": _result_round(total_available_ebitda, 2),
        "debt_service_coverage_ratio_dscr": _result_round(dscr, 2),
        "post_purchase_cash_liquidity": _result_round(post_purchase_cash, 2),
        "payback_period_months": _result_round(payback_months, 1),
    }

    # Constraints Evaluation
    min_cash_floor = _decimal((constraints_override or {}).get("min_cash_reserve_floor", 150000.0))
    min_dscr = _decimal((constraints_override or {}).get("min_dscr", 1.25))
    max_payback = _decimal((constraints_override or {}).get("max_payback_months", 36.0))

    c_list: List[DecisionConstraintResult] = []

    # 1. Liquidity Floor: Post-purchase cash >= min_cash_floor (Hard)
    passed_liq = post_purchase_cash >= min_cash_floor
    c_list.append(DecisionConstraintResult(
        constraint_id="LIQUIDITY_FLOOR",
        label=f"Cash Reserve Remains Above ₹{min_cash_floor:,.0f}",
        is_hard_constraint=True,
        passed=passed_liq,
        threshold_value=_result_round(min_cash_floor, 2),
        actual_value=_result_round(post_purchase_cash, 2),
        comparison=">=",
        explanation=f"Post-purchase liquidity of ₹{post_purchase_cash:,.0f} preserves safe working capital buffer."
        if passed_liq else f"Down payment depletes cash reserves to ₹{post_purchase_cash:,.0f}, below safety floor of ₹{min_cash_floor:,.0f}.",
    ))

    # 2. DSCR Coverage >= 1.25 (Hard)
    passed_dscr = dscr >= min_dscr
    c_list.append(DecisionConstraintResult(
        constraint_id="DSCR_COVERAGE",
        label=f"Debt Service Coverage Ratio (DSCR) >= {min_dscr:.2f}",
        is_hard_constraint=True,
        passed=passed_dscr,
        threshold_value=_result_round(min_dscr, 2),
        actual_value=_result_round(dscr, 2),
        comparison=">=",
        explanation=f"Robust debt service coverage of {dscr:.2f}x adequately absorbs revenue fluctuations."
        if passed_dscr else f"DSCR of {dscr:.2f}x is below the safe lending threshold of {min_dscr:.2f}x.",
    ))

    # 3. Payback Period <= max_payback (Hard)
    passed_pb = payback_months <= max_payback
    c_list.append(DecisionConstraintResult(
        constraint_id="PAYBACK_TIMELINE",
        label=f"Capital Recouped Within {max_payback:.0f} Months",
        is_hard_constraint=True,
        passed=passed_pb,
        threshold_value=_result_round(max_payback, 1),
        actual_value=_result_round(payback_months, 1),
        comparison="<=",
        explanation=f"Full investment recouped in {payback_months:.1f} months."
        if passed_pb else f"Investment payback period ({payback_months:.1f} months) exceeds {max_payback:.0f} month horizon.",
    ))

    # 4. Positive Monthly Net Cash Flow after EMI (Hard)
    passed_cf = net_monthly_cash_flow > _ZERO
    c_list.append(DecisionConstraintResult(
        constraint_id="POSITIVE_CASH_FLOW",
        label="Monthly Net Cash Flow After Debt Service Is Positive",
        is_hard_constraint=True,
        passed=passed_cf,
        threshold_value=0.0,
        actual_value=_result_round(net_monthly_cash_flow, 2),
        comparison=">",
        explanation=f"Generates ₹{net_monthly_cash_flow:,.0f} net surplus cash every month after paying bank EMI."
        if passed_cf else f"Cash flow deficit of ₹{abs(net_monthly_cash_flow):,.0f}/month during debt repayment.",
    ))

    hard_passed = all(c.passed for c in c_list if c.is_hard_constraint)
    all_passed = all(c.passed for c in c_list)

    # Multi-alternative evaluation (Compare 3 financing strategies)
    alternatives: List[DecisionAlternativeEvaluation] = []

    # Alternative A: 3-Year Term Loan (Base)
    score_a = 85.0 if all_passed else (60.0 if hard_passed else 35.0)
    kpi_a = _compute_alternative_kpis(down_payment, net_monthly_cash_flow, monthly_operating_gain, tenure_months)
    alternatives.append(DecisionAlternativeEvaluation(
        alternative_id="ALT_LOAN_36M",
        name=f"Bank Term Loan ({tenure_months} months at {interest_rate_pct:g}% interest)",
        outcome=DecisionOutcome.FEASIBLE if all_passed else (DecisionOutcome.CONDITIONALLY_FEASIBLE if hard_passed else DecisionOutcome.NOT_FEASIBLE),
        rank=1 if all_passed else 2,
        score=score_a,
        metrics={
            "down_payment": _result_round(down_payment, 2),
            "monthly_emi": _result_round(emi, 2),
            "net_monthly_cash_flow": _result_round(net_monthly_cash_flow, 2),
            "monthly_net_cash_impact": _result_round(net_monthly_cash_flow, 2),
            "dscr": _result_round(dscr, 2),
            "payback_months": kpi_a["payback_period_months"],
            "payback_period_months": kpi_a["payback_period_months"],
            "npv_amount": kpi_a["npv_amount"],
            "npv": kpi_a["npv_amount"],
            "roi_pct": kpi_a["roi_pct"],
            "irr_pct": kpi_a["irr_pct"],
        },
        constraints=c_list,
        explanation="Balanced debt tenure minimizing total interest while maintaining comfortable debt service coverage.",
    ))

    # Alternative B: 5-Year Term Loan (60 Months)
    emi_60 = _monthly_installment(loan_amount, rate_fraction, 60) if loan_amount > _ZERO else _ZERO
    cf_60 = monthly_operating_gain - emi_60
    dscr_60 = (total_available_ebitda / emi_60) if emi_60 > _ZERO else Decimal("999")
    c_list_b = [
        c_list[0],  # same liquidity
        DecisionConstraintResult("DSCR_60M", "DSCR >= 1.25", True, dscr_60 >= min_dscr, _result_round(min_dscr, 2), _result_round(dscr_60, 2), ">=", "Excellent debt coverage due to lower EMI."),
        c_list[2],  # same payback
        DecisionConstraintResult("CF_60M", "Net Cash Flow > 0", True, cf_60 > _ZERO, 0.0, _result_round(cf_60, 2), ">=", f"Higher monthly surplus of ₹{cf_60:,.0f}."),
    ]
    all_b = all(c.passed for c in c_list_b)
    kpi_b = _compute_alternative_kpis(down_payment, cf_60, cf_60, 60)
    alternatives.append(DecisionAlternativeEvaluation(
        alternative_id="ALT_LOAN_60M",
        name=f"Extended Bank Term Loan (60 months at {interest_rate_pct:g}% interest)",
        outcome=DecisionOutcome.FEASIBLE if all_b else DecisionOutcome.CONDITIONALLY_FEASIBLE,
        rank=2 if all_passed else 1,
        score=80.0 if all_b else 55.0,
        metrics={
            "down_payment": _result_round(down_payment, 2),
            "monthly_emi": _result_round(emi_60, 2),
            "net_monthly_cash_flow": _result_round(cf_60, 2),
            "monthly_net_cash_impact": _result_round(cf_60, 2),
            "dscr": _result_round(dscr_60, 2),
            "payback_months": kpi_b["payback_period_months"],
            "payback_period_months": kpi_b["payback_period_months"],
            "npv_amount": kpi_b["npv_amount"],
            "npv": kpi_b["npv_amount"],
            "roi_pct": kpi_b["roi_pct"],
            "irr_pct": kpi_b["irr_pct"],
        },
        constraints=c_list_b,
        explanation="Maximizes monthly operating cash flow cushion, though total interest paid over 5 years is higher.",
    ))

    # Alternative C: 100% Cash Purchase (No Debt)
    post_cash_c = current_cash_liquidity - machine_cost
    passed_liq_c = post_cash_c >= min_cash_floor
    c_list_c = [
        DecisionConstraintResult("LIQUIDITY_100_CASH", "Cash Above Safety Floor", True, passed_liq_c, _result_round(min_cash_floor, 2), _result_round(post_cash_c, 2), ">=", "Requires total cash drainage."),
        DecisionConstraintResult("DSCR_ZERO_DEBT", "DSCR (No Debt)", True, True, 1.0, 999.0, ">=", "Zero debt risk."),
        c_list[2],
        DecisionConstraintResult("CF_ZERO_DEBT", "Net Cash Flow", True, monthly_operating_gain > _ZERO, 0.0, _result_round(monthly_operating_gain, 2), ">=", f"Full ₹{monthly_operating_gain:,.0f} retained."),
    ]
    kpi_c = _compute_alternative_kpis(machine_cost, monthly_operating_gain, monthly_operating_gain, 0)
    alternatives.append(DecisionAlternativeEvaluation(
        alternative_id="ALT_SELF_FINANCED",
        name="100% Self-Financed from Internal Cash (Zero Debt)",
        outcome=DecisionOutcome.FEASIBLE if passed_liq_c else DecisionOutcome.NOT_FEASIBLE,
        rank=3,
        score=45.0 if not passed_liq_c else 75.0,
        metrics={
            "down_payment": _result_round(machine_cost, 2),
            "monthly_emi": 0.0,
            "net_monthly_cash_flow": _result_round(monthly_operating_gain, 2),
            "monthly_net_cash_impact": _result_round(monthly_operating_gain, 2),
            "dscr": 999.0,
            "payback_months": kpi_c["payback_period_months"],
            "payback_period_months": kpi_c["payback_period_months"],
            "npv_amount": kpi_c["npv_amount"],
            "npv": kpi_c["npv_amount"],
            "roi_pct": kpi_c["roi_pct"],
            "irr_pct": kpi_c["irr_pct"],
        },
        constraints=c_list_c,
        explanation="Avoids bank interest entirely, but severely depletes internal liquidity if cash reserves are insufficient.",
    ))

    # Sort alternatives by rank
    alternatives.sort(key=lambda a: a.rank)

    if all_passed:
        outcome = DecisionOutcome.FEASIBLE
        summary = f"Procurement of {machine_name} is FEASIBLE. The 3-year bank loan maintains ₹{post_purchase_cash:,.0f} cash reserves, achieves {dscr:.2f}x DSCR, and delivers ₹{net_monthly_cash_flow:,.0f}/month net cash surplus."
    elif hard_passed:
        outcome = DecisionOutcome.CONDITIONALLY_FEASIBLE
        summary = f"Procurement of {machine_name} is CONDITIONALLY FEASIBLE. Debt coverage is acceptable but cash reserve margin is tight."
    else:
        outcome = DecisionOutcome.NOT_FEASIBLE
        failed_names = [c.label for c in c_list if c.is_hard_constraint and not c.passed]
        summary = f"Procurement of {machine_name} is NOT FEASIBLE. Violates critical financial thresholds: {', '.join(failed_names)}."

    # Graph
    nodes = [
        DecisionGraphNode("in_cost", f"Machine Cost: ₹{machine_cost:,.0f}", DecisionNodeType.INPUT, machine_cost, "Capital Expenditure", "INR"),
        DecisionGraphNode("in_dp", f"Down Payment: ₹{down_payment:,.0f}", DecisionNodeType.INPUT, down_payment, "Cash Outlay", "INR"),
        DecisionGraphNode("in_loan", f"Loan: ₹{loan_amount:,.0f}", DecisionNodeType.INPUT, loan_amount, "Debt Principal", "INR"),
        DecisionGraphNode("calc_emi", f"EMI: ₹{emi:,.0f}/mo", DecisionNodeType.CALCULATION, emi, "Monthly Debt Service", "INR"),
        DecisionGraphNode("calc_gain", f"Operating Gain: ₹{monthly_operating_gain:,.0f}/mo", DecisionNodeType.CALCULATION, monthly_operating_gain, "Incremental Gross Profit less Maintenance", "INR"),
        DecisionGraphNode("calc_net_cf", f"Net Cash Flow: ₹{net_monthly_cash_flow:,.0f}/mo", DecisionNodeType.CALCULATION, net_monthly_cash_flow, "Operating Gain less EMI", "INR"),
        DecisionGraphNode("calc_dscr", f"DSCR: {dscr:.2f}x", DecisionNodeType.CALCULATION, dscr, "Debt Service Coverage Ratio", "ratio"),
        DecisionGraphNode("calc_cash", f"Post-Purchase Cash: ₹{post_purchase_cash:,.0f}", DecisionNodeType.CALCULATION, post_purchase_cash, "Ending Liquidity", "INR"),
        DecisionGraphNode("out_decision", f"Outcome: {outcome.value}", DecisionNodeType.OUTCOME, outcome.value, summary),
    ]
    edges = [
        DecisionGraphEdge("in_cost", "in_loan"),
        DecisionGraphEdge("in_dp", "in_loan"),
        DecisionGraphEdge("in_loan", "calc_emi"),
        DecisionGraphEdge("calc_gain", "calc_net_cf"),
        DecisionGraphEdge("calc_emi", "calc_net_cf"),
        DecisionGraphEdge("calc_gain", "calc_dscr"),
        DecisionGraphEdge("calc_emi", "calc_dscr"),
        DecisionGraphEdge("in_dp", "calc_cash"),
        DecisionGraphEdge("calc_net_cf", "out_decision"),
        DecisionGraphEdge("calc_dscr", "out_decision"),
        DecisionGraphEdge("calc_cash", "out_decision"),
    ]

    return DecisionEvaluationResult(
        model_id="MACHINE_OR_EQUIPMENT_PURCHASE",
        model_version="1.0.0",
        objective=f"Evaluate capital purchase of {machine_name}",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        recommended_alternative=alternatives[0].name if alternatives else None,
        alternatives=alternatives,
        graph_nodes=nodes,
        graph_edges=edges,
    )


# ==============================================================================
# 4. Model 3: SUPPLIER_SWITCH_OR_CREDIT_TERMS (v1.0.0)
# ==============================================================================

def evaluate_supplier_switch(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """Evaluates switching raw material supplier or renegotiating credit payment terms."""
    supplier_name = str(inputs.get("new_supplier_name", "Alternative Supplier"))
    current_price = _decimal(inputs.get("current_unit_price", 0.0))
    new_price = _decimal(inputs.get("new_unit_price", 0.0))
    monthly_units = _decimal(inputs.get("monthly_units", 0.0))
    current_credit_days = int(inputs.get("current_credit_days", 15))
    new_credit_days = int(inputs.get("new_credit_days", 30))
    switching_cost = _decimal(inputs.get("switching_cost", 0.0))

    if current_price <= _ZERO or monthly_units <= _ZERO:
        return DecisionEvaluationResult(
            model_id="SUPPLIER_SWITCH_OR_CREDIT_TERMS",
            model_version="1.0.0",
            objective=f"Evaluate supplier transition to {supplier_name}",
            inputs=inputs,
            calculations={},
            constraints=[],
            outcome=DecisionOutcome.INSUFFICIENT_INFORMATION,
            summary_explanation="Current unit price and monthly units must be positive.",
        )

    price_diff_per_unit = current_price - new_price
    monthly_price_savings = price_diff_per_unit * monthly_units
    annual_price_savings = monthly_price_savings * _TWELVE

    # Working capital benefit from credit day extension
    credit_days_diff = new_credit_days - current_credit_days
    daily_procurement = (new_price * monthly_units) / _THIRTY
    working_capital_freed = daily_procurement * credit_days_diff
    cost_of_capital = _decimal((constraints_override or {}).get("annual_cost_of_capital_pct", 12.0)) / _HUNDRED
    annual_capital_interest_saving = working_capital_freed * cost_of_capital

    total_annual_benefit = annual_price_savings + annual_capital_interest_saving - switching_cost

    calculations = {
        "price_difference_per_unit": _result_round(price_diff_per_unit, 2),
        "monthly_price_savings": _result_round(monthly_price_savings, 2),
        "annual_price_savings": _result_round(annual_price_savings, 2),
        "working_capital_freed_up": _result_round(working_capital_freed, 2),
        "annual_capital_interest_saving": _result_round(annual_capital_interest_saving, 2),
        "total_first_year_net_benefit": _result_round(total_annual_benefit, 2),
    }

    c_list: List[DecisionConstraintResult] = [
        DecisionConstraintResult(
            "POSITIVE_ANNUAL_BENEFIT",
            "Total First-Year Benefit Exceeds Switching Cost",
            True,
            total_annual_benefit > _ZERO,
            0.0,
            _result_round(total_annual_benefit, 2),
            ">",
            f"Net positive gain of ₹{total_annual_benefit:,.0f} in year one."
            if total_annual_benefit > _ZERO else "Switching cost outweighs combined procurement savings.",
        ),
        DecisionConstraintResult(
            "NON_NEGATIVE_CREDIT_TERMS",
            "Credit Terms Do Not Worsen",
            False,
            new_credit_days >= current_credit_days,
            current_credit_days,
            new_credit_days,
            ">=",
            f"Credit terms extended from {current_credit_days} to {new_credit_days} days."
            if new_credit_days >= current_credit_days else f"Credit terms reduced by {abs(credit_days_diff)} days.",
        ),
    ]

    hard_passed = all(c.passed for c in c_list if c.is_hard_constraint)
    all_passed = all(c.passed for c in c_list)

    outcome = DecisionOutcome.FEASIBLE if all_passed else (DecisionOutcome.CONDITIONALLY_FEASIBLE if hard_passed else DecisionOutcome.NOT_FEASIBLE)
    summary = f"Switching to {supplier_name} is {outcome.value}. Delivers ₹{monthly_price_savings:,.0f}/month direct savings and frees ₹{working_capital_freed:,.0f} in working capital."

    monthly_gain_eff = monthly_price_savings + (annual_capital_interest_saving / Decimal("12"))
    initial_outflow_eff = max(switching_cost - working_capital_freed, Decimal("0"))
    alt_supplier = _build_comparative_alternatives(
        "SUPPLIER_SWITCH", supplier_name, initial_outflow_eff, monthly_gain_eff, outcome, c_list
    )

    return DecisionEvaluationResult(
        model_id="SUPPLIER_SWITCH_OR_CREDIT_TERMS",
        model_version="1.0.0",
        objective=f"Evaluate supplier transition to {supplier_name}",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        alternatives=alt_supplier,
    )


# ==============================================================================
# 5. Model 4: BULK_DISCOUNT_VS_STORAGE_COST (v1.0.0)
# ==============================================================================

def evaluate_bulk_discount(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """Evaluates whether volume discount outweighs warehouse holding cost and capital lockup."""
    regular_price = _decimal(inputs.get("regular_unit_price", 0.0))
    discounted_price = _decimal(inputs.get("discounted_unit_price", 0.0))
    order_qty = _decimal(inputs.get("order_quantity", 0.0))
    monthly_consumption = _decimal(inputs.get("monthly_consumption", 0.0))
    monthly_storage_per_unit = _decimal(inputs.get("monthly_storage_per_unit", 1.5))
    cost_of_capital_pct = _decimal(inputs.get("annual_cost_of_capital_pct", 12.0)) / _HUNDRED

    if regular_price <= _ZERO or order_qty <= _ZERO or monthly_consumption <= _ZERO:
        return DecisionEvaluationResult(
            model_id="BULK_DISCOUNT_VS_STORAGE_COST",
            model_version="1.0.0",
            objective="Evaluate bulk procurement discount vs holding costs",
            inputs=inputs,
            calculations={},
            constraints=[],
            outcome=DecisionOutcome.INSUFFICIENT_INFORMATION,
            summary_explanation="Regular price, order quantity, and consumption rate must be positive.",
        )

    holding_months = order_qty / monthly_consumption
    discount_savings = (regular_price - discounted_price) * order_qty
    # Average inventory held over the period = order_qty / 2
    avg_inventory = order_qty / Decimal("2")
    total_storage_cost = avg_inventory * monthly_storage_per_unit * holding_months
    capital_locked = avg_inventory * discounted_price
    capital_cost = capital_locked * (cost_of_capital_pct / _TWELVE) * holding_months

    net_benefit = discount_savings - total_storage_cost - capital_cost

    calculations = {
        "holding_months": _result_round(holding_months, 1),
        "gross_discount_savings": _result_round(discount_savings, 2),
        "total_storage_cost": _result_round(total_storage_cost, 2),
        "capital_carrying_cost": _result_round(capital_cost, 2),
        "net_bulk_savings": _result_round(net_benefit, 2),
    }

    c_list: List[DecisionConstraintResult] = [
        DecisionConstraintResult(
            "POSITIVE_NET_BENEFIT",
            "Net Bulk Savings Greater Than Zero",
            True,
            net_benefit > _ZERO,
            0.0,
            _result_round(net_benefit, 2),
            ">",
            f"Bulk discount yields net economic surplus of ₹{net_benefit:,.0f}."
            if net_benefit > _ZERO else f"Storage and capital carrying costs exceed discount savings by ₹{abs(net_benefit):,.0f}.",
        ),
        DecisionConstraintResult(
            "HOLDING_HORIZON_SAFE",
            "Inventory Depleted Within 6 Months (Spoilage / Obsolescence Safe)",
            False,
            holding_months <= Decimal("6"),
            6.0,
            _result_round(holding_months, 1),
            "<=",
            f"Stock consumed in {holding_months:.1f} months."
            if holding_months <= Decimal("6") else f"Holding period ({holding_months:.1f} mos) exceeds recommended 6-month limit.",
        ),
    ]

    all_passed = all(c.passed for c in c_list)
    hard_passed = all(c.passed for c in c_list if c.is_hard_constraint)
    outcome = DecisionOutcome.FEASIBLE if all_passed else (DecisionOutcome.CONDITIONALLY_FEASIBLE if hard_passed else DecisionOutcome.NOT_FEASIBLE)
    summary = f"Bulk purchase is {outcome.value}. Generates ₹{discount_savings:,.0f} gross discount, net ₹{net_benefit:,.0f} after carrying costs."

    monthly_gain_bulk = net_benefit / Decimal("12")
    initial_outflow_bulk = order_qty * discounted_price
    alt_bulk = _build_comparative_alternatives(
        "BULK_DISCOUNT", "Bulk Volume Consignment", initial_outflow_bulk, monthly_gain_bulk, outcome, c_list
    )

    return DecisionEvaluationResult(
        model_id="BULK_DISCOUNT_VS_STORAGE_COST",
        model_version="1.0.0",
        objective="Evaluate bulk procurement discount vs holding costs",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        alternatives=alt_bulk,
    )


# ==============================================================================
# 6. Model 5: NEW_BRANCH_OR_LOCATION_OPENING (v1.0.0)
# ==============================================================================

def evaluate_new_location_opening(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """Evaluates commercial retail/outlet expansion with setup capex, rent, and breakeven."""
    location_name = str(inputs.get("location_name", "New Branch"))
    fitout_capex = _decimal(inputs.get("fitout_capex", 0.0))
    security_deposit = _decimal(inputs.get("security_deposit", 0.0))
    monthly_rent = _decimal(inputs.get("monthly_rent", 0.0))
    monthly_staff_cost = _decimal(inputs.get("monthly_staff_cost", 0.0))
    monthly_utilities = _decimal(inputs.get("monthly_utilities", 0.0))
    expected_daily_customers = _decimal(inputs.get("expected_daily_customers", 0.0))
    average_order_value = _decimal(inputs.get("average_order_value", 0.0))
    gross_margin_pct = _decimal(inputs.get("gross_margin_pct", 40.0)) / _HUNDRED

    total_upfront_outlay = fitout_capex + security_deposit
    monthly_fixed_overhead = monthly_rent + monthly_staff_cost + monthly_utilities
    expected_monthly_revenue = expected_daily_customers * _THIRTY * average_order_value
    expected_monthly_gross_profit = expected_monthly_revenue * gross_margin_pct
    expected_monthly_ebitda = expected_monthly_gross_profit - monthly_fixed_overhead

    break_even_monthly_revenue = (monthly_fixed_overhead / gross_margin_pct) if gross_margin_pct > _ZERO else Decimal("999999")
    payback_months = (total_upfront_outlay / expected_monthly_ebitda) if expected_monthly_ebitda > _ZERO else Decimal("999")

    calculations = {
        "total_upfront_outlay": _result_round(total_upfront_outlay, 2),
        "monthly_fixed_overhead": _result_round(monthly_fixed_overhead, 2),
        "expected_monthly_revenue": _result_round(expected_monthly_revenue, 2),
        "expected_monthly_gross_profit": _result_round(expected_monthly_gross_profit, 2),
        "expected_monthly_ebitda": _result_round(expected_monthly_ebitda, 2),
        "break_even_monthly_revenue": _result_round(break_even_monthly_revenue, 2),
        "payback_period_months": _result_round(payback_months, 1),
    }

    c_list: List[DecisionConstraintResult] = [
        DecisionConstraintResult(
            "POSITIVE_BRANCH_EBITDA",
            "Monthly Operating Profit (EBITDA) Is Positive",
            True,
            expected_monthly_ebitda > _ZERO,
            0.0,
            _result_round(expected_monthly_ebitda, 2),
            ">",
            f"Generates ₹{expected_monthly_ebitda:,.0f}/month operating profit above overhead."
            if expected_monthly_ebitda > _ZERO else "Branch operates at a monthly cash loss.",
        ),
        DecisionConstraintResult(
            "PAYBACK_WITHIN_24_MONTHS",
            "Upfront Fitout & Deposit Recouped Within 24 Months",
            True,
            payback_months <= Decimal("24"),
            24.0,
            _result_round(payback_months, 1),
            "<=",
            f"Capital recouped in {payback_months:.1f} months."
            if payback_months <= Decimal("24") else f"Payback ({payback_months:.1f} months) exceeds 24-month target.",
        ),
    ]

    all_passed = all(c.passed for c in c_list)
    outcome = DecisionOutcome.FEASIBLE if all_passed else DecisionOutcome.NOT_FEASIBLE
    summary = f"Opening branch at {location_name} is {outcome.value}. Expected monthly revenue ₹{expected_monthly_revenue:,.0f} against breakeven threshold of ₹{break_even_monthly_revenue:,.0f}."

    alt_location = _build_comparative_alternatives(
        "NEW_BRANCH", location_name, total_upfront_outlay, expected_monthly_ebitda, outcome, c_list
    )

    return DecisionEvaluationResult(
        model_id="NEW_BRANCH_OR_LOCATION_OPENING",
        model_version="1.0.0",
        objective=f"Evaluate opening new location at {location_name}",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        alternatives=alt_location,
    )


# ==============================================================================
# 7. Model 6: HIRING_STAFF_OR_COMMISSION (v1.0.0)
# ==============================================================================

def evaluate_staff_hiring(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """Evaluates hiring full-time operational staff vs performance commission."""
    role_title = str(inputs.get("role_title", "Sales Specialist"))
    monthly_fixed_salary = _decimal(inputs.get("monthly_fixed_salary", 0.0))
    commission_pct = _decimal(inputs.get("commission_pct", 0.0)) / _HUNDRED
    benefits_overhead = _decimal(inputs.get("benefits_and_overhead", 0.0))
    expected_incremental_revenue = _decimal(inputs.get("expected_incremental_revenue", 0.0))
    gross_margin_pct = _decimal(inputs.get("gross_margin_pct", 35.0)) / _HUNDRED

    total_fixed_cost = monthly_fixed_salary + benefits_overhead
    commission_cost = expected_incremental_revenue * commission_pct
    total_employment_cost = total_fixed_cost + commission_cost
    gross_profit_generated = expected_incremental_revenue * gross_margin_pct
    net_monthly_contribution = gross_profit_generated - total_employment_cost

    # Minimum sales needed to break even on employee
    break_even_sales = (total_fixed_cost / (gross_margin_pct - commission_pct)) if (gross_margin_pct - commission_pct) > _ZERO else Decimal("999999")

    calculations = {
        "total_monthly_employment_cost": _result_round(total_employment_cost, 2),
        "gross_profit_generated": _result_round(gross_profit_generated, 2),
        "net_monthly_contribution": _result_round(net_monthly_contribution, 2),
        "break_even_monthly_sales_required": _result_round(break_even_sales, 2),
    }

    c_list: List[DecisionConstraintResult] = [
        DecisionConstraintResult(
            "POSITIVE_STAFF_CONTRIBUTION",
            "Net Monthly Financial Contribution Is Positive",
            True,
            net_monthly_contribution > _ZERO,
            0.0,
            _result_round(net_monthly_contribution, 2),
            ">",
            f"Hiring delivers ₹{net_monthly_contribution:,.0f}/month net business surplus."
            if net_monthly_contribution > _ZERO else "Staff cost exceeds expected gross margin contribution.",
        ),
    ]

    outcome = DecisionOutcome.FEASIBLE if net_monthly_contribution > _ZERO else DecisionOutcome.NOT_FEASIBLE
    summary = f"Hiring for {role_title} is {outcome.value}. Requires ₹{break_even_sales:,.0f}/month in incremental sales to cover payroll burden."

    alt_staff = _build_comparative_alternatives(
        "STAFF_HIRING", role_title, Decimal("0"), net_monthly_contribution, outcome, c_list
    )

    return DecisionEvaluationResult(
        model_id="HIRING_STAFF_OR_COMMISSION",
        model_version="1.0.0",
        objective=f"Evaluate hiring {role_title}",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        alternatives=alt_staff,
    )


# ==============================================================================
# 8. Model 7: CREDIT_TERM_EXTENSION_TO_CUSTOMER (v1.0.0)
# ==============================================================================

def evaluate_credit_term_extension(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """Evaluates extending customer payment terms to stimulate sales volume."""
    customer_name = str(inputs.get("customer_name", "Key Account"))
    current_monthly_sales = _decimal(inputs.get("current_monthly_sales", 0.0))
    expected_sales_increase_pct = _decimal(inputs.get("expected_sales_increase_pct", 20.0)) / _HUNDRED
    current_terms_days = int(inputs.get("current_terms_days", 15))
    proposed_terms_days = int(inputs.get("proposed_terms_days", 45))
    gross_margin_pct = _decimal(inputs.get("gross_margin_pct", 30.0)) / _HUNDRED
    default_risk_pct = _decimal(inputs.get("default_risk_pct", 2.0)) / _HUNDRED
    annual_cost_of_capital_pct = _decimal(inputs.get("annual_cost_of_capital_pct", 12.0)) / _HUNDRED

    new_monthly_sales = current_monthly_sales * (_ONE + expected_sales_increase_pct)
    incremental_sales = new_monthly_sales - current_monthly_sales
    incremental_gross_profit = incremental_sales * gross_margin_pct

    # Receivables locked
    old_receivables = (current_monthly_sales / _THIRTY) * current_terms_days
    new_receivables = (new_monthly_sales / _THIRTY) * proposed_terms_days
    additional_receivables_locked = new_receivables - old_receivables

    monthly_carrying_cost = additional_receivables_locked * (annual_cost_of_capital_pct / _TWELVE)
    monthly_bad_debt_provision = new_monthly_sales * default_risk_pct

    net_monthly_gain = incremental_gross_profit - monthly_carrying_cost - monthly_bad_debt_provision

    calculations = {
        "new_monthly_sales": _result_round(new_monthly_sales, 2),
        "incremental_gross_profit": _result_round(incremental_gross_profit, 2),
        "additional_receivables_locked": _result_round(additional_receivables_locked, 2),
        "monthly_carrying_cost_of_debt": _result_round(monthly_carrying_cost, 2),
        "monthly_bad_debt_provision": _result_round(monthly_bad_debt_provision, 2),
        "net_monthly_economic_gain": _result_round(net_monthly_gain, 2),
    }

    c_list: List[DecisionConstraintResult] = [
        DecisionConstraintResult(
            "POSITIVE_NET_CREDIT_GAIN",
            "Incremental Profit Outweighs Capital Cost & Default Risk",
            True,
            net_monthly_gain > _ZERO,
            0.0,
            _result_round(net_monthly_gain, 2),
            ">",
            f"Delivers ₹{net_monthly_gain:,.0f}/month net gain after bad debt provision."
            if net_monthly_gain > _ZERO else "Working capital drag and default risk exceed incremental profit.",
        ),
    ]

    outcome = DecisionOutcome.FEASIBLE if net_monthly_gain > _ZERO else DecisionOutcome.NOT_FEASIBLE
    summary = f"Extending credit terms to {customer_name} is {outcome.value}. Net monthly gain ₹{net_monthly_gain:,.0f} with ₹{additional_receivables_locked:,.0f} working capital locked."

    alt_credit = _build_comparative_alternatives(
        "CREDIT_EXTENSION", customer_name, additional_receivables_locked, net_monthly_gain, outcome, c_list
    )

    return DecisionEvaluationResult(
        model_id="CREDIT_TERM_EXTENSION_TO_CUSTOMER",
        model_version="1.0.0",
        objective=f"Evaluate credit extension for {customer_name}",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        alternatives=alt_credit,
    )


# ==============================================================================
# 9. Model 8: PRICE_INCREASE_OR_DISCOUNT (v1.0.0)
# ==============================================================================

def evaluate_price_change(
    inputs: Dict[str, Any],
    constraints_override: Optional[Dict[str, Any]] = None,
) -> DecisionEvaluationResult:
    """Evaluates elasticity impact of increasing or discounting product selling price."""
    product_name = str(inputs.get("product_name", "Core Product"))
    current_price = _decimal(inputs.get("current_price", 0.0))
    proposed_price = _decimal(inputs.get("proposed_price", 0.0))
    current_volume = _decimal(inputs.get("current_monthly_volume", 0.0))
    unit_variable_cost = _decimal(inputs.get("unit_variable_cost", 0.0))
    price_elasticity = _decimal(inputs.get("price_elasticity_of_demand", -1.2))  # Typically negative

    if current_price <= _ZERO or proposed_price <= _ZERO or current_volume <= _ZERO:
        return DecisionEvaluationResult(
            model_id="PRICE_INCREASE_OR_DISCOUNT",
            model_version="1.0.0",
            objective=f"Evaluate price adjustment for {product_name}",
            inputs=inputs,
            calculations={},
            constraints=[],
            outcome=DecisionOutcome.INSUFFICIENT_INFORMATION,
            summary_explanation="Current price, proposed price, and volume must be positive.",
        )

    price_change_pct = (proposed_price - current_price) / current_price
    volume_change_pct = price_change_pct * price_elasticity
    new_volume = max(_ZERO, current_volume * (_ONE + volume_change_pct))

    current_rev = current_volume * current_price
    current_profit = current_volume * (current_price - unit_variable_cost)

    new_rev = new_volume * proposed_price
    new_profit = new_volume * (proposed_price - unit_variable_cost)
    profit_diff = new_profit - current_profit

    calculations = {
        "price_change_percent": _result_round(price_change_pct * _HUNDRED, 2),
        "projected_volume_change_percent": _result_round(volume_change_pct * _HUNDRED, 2),
        "projected_monthly_volume": _result_round(new_volume, 0),
        "current_monthly_profit": _result_round(current_profit, 2),
        "projected_monthly_profit": _result_round(new_profit, 2),
        "net_monthly_profit_difference": _result_round(profit_diff, 2),
    }

    c_list: List[DecisionConstraintResult] = [
        DecisionConstraintResult(
            "NET_PROFIT_IMPROVED",
            "Adjusted Price Increases Overall Monthly Net Profit",
            True,
            profit_diff > _ZERO,
            0.0,
            _result_round(profit_diff, 2),
            ">",
            f"Price adjustment expands monthly profit by ₹{profit_diff:,.0f}."
            if profit_diff > _ZERO else f"Demand volume drop erodes monthly profit by ₹{abs(profit_diff):,.0f}.",
        ),
    ]

    outcome = DecisionOutcome.FEASIBLE if profit_diff > _ZERO else DecisionOutcome.NOT_FEASIBLE
    summary = f"Price change for {product_name} is {outcome.value}. Profit changes by ₹{profit_diff:,.0f}/month at elasticity {price_elasticity:.2f}."

    alt_price = _build_comparative_alternatives(
        "PRICE_CHANGE", product_name, Decimal("0"), profit_diff, outcome, c_list
    )

    return DecisionEvaluationResult(
        model_id="PRICE_INCREASE_OR_DISCOUNT",
        model_version="1.0.0",
        objective=f"Evaluate price adjustment for {product_name}",
        inputs=inputs,
        calculations=calculations,
        constraints=c_list,
        outcome=outcome,
        summary_explanation=summary,
        alternatives=alt_price,
    )


def _additional_evaluator(function_name: str):
    """Load secondary evaluators at execution time to keep the strategy modules acyclic."""
    def evaluate(inputs: Dict[str, Any], constraints_override: Optional[Dict[str, Any]] = None):
        from backend.arthlens.decision import additional_models
        return getattr(additional_models, function_name)(inputs, constraints_override)
    return evaluate


# Registry of deterministic decision strategies.
DECISION_MODEL_REGISTRY: Dict[str, Callable[[Dict[str, Any], Optional[Dict[str, Any]]], DecisionEvaluationResult]] = {
    "NEW_PRODUCT_ADDITION": evaluate_new_product_addition,
    "MACHINE_OR_EQUIPMENT_PURCHASE": evaluate_equipment_purchase,
    "SUPPLIER_SWITCH_OR_CREDIT_TERMS": evaluate_supplier_switch,
    "BULK_DISCOUNT_VS_STORAGE_COST": evaluate_bulk_discount,
    "NEW_BRANCH_OR_LOCATION_OPENING": evaluate_new_location_opening,
    "HIRING_STAFF_OR_COMMISSION": evaluate_staff_hiring,
    "CREDIT_TERM_EXTENSION_TO_CUSTOMER": evaluate_credit_term_extension,
    "PRICE_INCREASE_OR_DISCOUNT": evaluate_price_change,
    "FINANCING_COMPARISON": _additional_evaluator("evaluate_financing_comparison"),
    "BUSINESS_EXPANSION": _additional_evaluator("evaluate_business_expansion"),
    "INVENTORY_PROCUREMENT": _additional_evaluator("evaluate_inventory_procurement"),
    "CUSTOMER_CREDIT_RISK": _additional_evaluator("evaluate_customer_credit_risk"),
    "COST_REDUCTION": _additional_evaluator("evaluate_cost_reduction"),
    "CASH_FLOW_PRESSURE": _additional_evaluator("evaluate_cash_flow_pressure"),
    "BUSINESS_VIABILITY": _additional_evaluator("evaluate_business_viability"),
    "LOCATION_SELECTION": _additional_evaluator("evaluate_location_selection"),
}
