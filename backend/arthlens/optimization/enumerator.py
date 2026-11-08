"""
Discrete Alternative Strategy and Site Enumeration Optimizer.

Authoritative Reference:
- ArthLens Build Handbook v1.0 (Section 2.1, 2.2 #24, 2.3 Loop B, Part 8).
- Scope: MVP uses explicit enumeration for small sets of 2–3 user-chosen or suggested sites/strategies.
- Output: Deterministic ranking with assumption labels, constraint validation, and follow-up tasks.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


class OptimizationObjective(str, Enum):
    MAXIMIZE_NET_CASH_FLOW = "maximize_net_cash_flow"
    MINIMIZE_BREAK_EVEN_UNITS = "minimize_break_even_units"
    MAXIMIZE_CONTRIBUTION_MARGIN = "maximize_contribution_margin"
    MAXIMIZE_ROI = "maximize_roi"


@dataclass(frozen=True)
class CandidateAlternative:
    """A discrete business or siting alternative evaluated by the optimizer."""

    id: str
    name: str
    capital_expenditure: float
    price_per_unit: float
    variable_cost_per_unit: float
    fixed_costs_per_month: float
    target_monthly_volume: float
    site_coordinate: tuple[float, float] | None = None
    geo_unit_id: str | None = None
    is_osm_suggestion: bool = False
    zoning_verified: bool = False
    custom_attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluatedAlternative:
    """Evaluated financial and operational metrics for a candidate alternative."""

    alternative: CandidateAlternative
    rank: int
    is_feasible: bool
    contribution_margin: float
    break_even_units: float
    monthly_revenue: float
    monthly_total_cost: float
    monthly_net_cash_flow: float
    annual_roi_percent: float
    constraint_violations: tuple[str, ...] = ()
    assumption_labels: tuple[str, ...] = ()
    followup_tasks: tuple[str, ...] = ()


@dataclass(frozen=True)
class OptimizationResult:
    """Deterministic result of the discrete alternative enumeration."""

    objective: OptimizationObjective
    total_candidates: int
    ranked_alternatives: tuple[EvaluatedAlternative, ...]
    infeasible_alternatives: tuple[EvaluatedAlternative, ...]
    recommended_alternative: EvaluatedAlternative | None
    generated_followup_tasks: tuple[str, ...]
    as_of: str
    optimizer_version: str = "v1.0.0-enumeration"


def enumerate_and_rank_alternatives(
    candidates: Sequence[CandidateAlternative],
    *,
    objective: OptimizationObjective = OptimizationObjective.MAXIMIZE_NET_CASH_FLOW,
    max_capital_budget: float | None = None,
    max_allowable_break_even_units: float | None = None,
    min_required_net_cash_flow: float | None = None,
) -> OptimizationResult:
    """
    Deterministically enumerate and rank 2-3 discrete strategy or siting candidates.

    Rejects non-finite values, validates explicit constraints, labels unverified assumptions
    (such as OSM suggestions lacking zoning verification), and generates necessary follow-up tasks.
    """
    if not candidates:
        return OptimizationResult(
            objective=objective,
            total_candidates=0,
            ranked_alternatives=(),
            infeasible_alternatives=(),
            recommended_alternative=None,
            generated_followup_tasks=(),
            as_of=datetime.now(timezone.utc).isoformat(),
        )

    evaluated_list: list[EvaluatedAlternative] = []
    all_followups: list[str] = []

    for cand in candidates:
        violations: list[str] = []
        assumptions: list[str] = []
        cand_followups: list[str] = []

        # Validate non-finite inputs
        for field_name, val in [
            ("capital_expenditure", cand.capital_expenditure),
            ("price_per_unit", cand.price_per_unit),
            ("variable_cost_per_unit", cand.variable_cost_per_unit),
            ("fixed_costs_per_month", cand.fixed_costs_per_month),
            ("target_monthly_volume", cand.target_monthly_volume),
        ]:
            if not isinstance(val, (int, float)) or val < 0 or val != val:  # NaN check
                violations.append(f"Invalid non-finite or negative value for {field_name}")

        # Compute core financial metrics
        cm = cand.price_per_unit - cand.variable_cost_per_unit
        if cm <= 0:
            violations.append(f"Non-positive contribution margin: {cm:.2f} INR/unit")
            break_even = float("inf")
        else:
            break_even = cand.fixed_costs_per_month / cm

        monthly_rev = cand.price_per_unit * cand.target_monthly_volume
        monthly_var_cost = cand.variable_cost_per_unit * cand.target_monthly_volume
        monthly_cost = cand.fixed_costs_per_month + monthly_var_cost
        monthly_net = monthly_rev - monthly_cost

        annual_profit = monthly_net * 12.0
        roi = (
            (annual_profit / cand.capital_expenditure * 100.0)
            if cand.capital_expenditure > 0
            else 0.0
        )

        # Check explicit constraints
        if max_capital_budget is not None and cand.capital_expenditure > max_capital_budget:
            violations.append(
                f"Capital expenditure ({cand.capital_expenditure:.2f}) exceeds budget ({max_capital_budget:.2f})"
            )

        if (
            max_allowable_break_even_units is not None
            and break_even > max_allowable_break_even_units
        ):
            violations.append(
                f"Break-even units ({break_even:.1f}) exceeds allowable limit ({max_allowable_break_even_units:.1f})"
            )

        if min_required_net_cash_flow is not None and monthly_net < min_required_net_cash_flow:
            violations.append(
                f"Monthly net cash flow ({monthly_net:.2f}) below required minimum ({min_required_net_cash_flow:.2f})"
            )

        # Assumption tracking & zoning caveats (Handbook Page 7)
        assumptions.append(f"Assumed monthly volume: {cand.target_monthly_volume:.0f} units")
        assumptions.append(f"Assumed unit price: {cand.price_per_unit:.2f} INR")

        if cand.is_osm_suggestion:
            assumptions.append("Location suggested from OpenStreetMap commercial/industrial tags")
            if not cand.zoning_verified:
                assumptions.append("Caveat: Site not checked for municipal zoning or lease availability")
                task = f"Verify municipal zoning, commercial permissions, and site availability for '{cand.name}'"
                cand_followups.append(task)
                all_followups.append(task)

        if cand.site_coordinate is not None and not cand.zoning_verified and not cand.is_osm_suggestion:
            task = f"Verify physical road accessibility and power utility hookup for site '{cand.name}'"
            cand_followups.append(task)
            all_followups.append(task)

        is_feas = len(violations) == 0

        evaluated_list.append(
            EvaluatedAlternative(
                alternative=cand,
                rank=0,  # Assigned after sorting
                is_feasible=is_feas,
                contribution_margin=cm,
                break_even_units=break_even if break_even != float("inf") else -1.0,
                monthly_revenue=monthly_rev,
                monthly_total_cost=monthly_cost,
                monthly_net_cash_flow=monthly_net,
                annual_roi_percent=roi,
                constraint_violations=tuple(violations),
                assumption_labels=tuple(assumptions),
                followup_tasks=tuple(cand_followups),
            )
        )

    # Deterministic sorting key based on objective
    def sort_key(item: EvaluatedAlternative) -> tuple[Any, ...]:
        if objective == OptimizationObjective.MAXIMIZE_NET_CASH_FLOW:
            score = item.monthly_net_cash_flow
            reverse_metric = -score
        elif objective == OptimizationObjective.MINIMIZE_BREAK_EVEN_UNITS:
            score = item.break_even_units
            reverse_metric = score  # smaller is better
        elif objective == OptimizationObjective.MAXIMIZE_CONTRIBUTION_MARGIN:
            score = item.contribution_margin
            reverse_metric = -score
        elif objective == OptimizationObjective.MAXIMIZE_ROI:
            score = item.annual_roi_percent
            reverse_metric = -score
        else:
            reverse_metric = -item.monthly_net_cash_flow

        # Secondary tie-breaker: alternative id (deterministic stability)
        return (reverse_metric, item.alternative.id)

    feasible_items = [item for item in evaluated_list if item.is_feasible]
    infeasible_items = [item for item in evaluated_list if not item.is_feasible]

    feasible_items.sort(key=sort_key)
    infeasible_items.sort(key=lambda x: x.alternative.id)

    # Assign sequential ranks
    ranked_final: list[EvaluatedAlternative] = []
    for rank_idx, item in enumerate(feasible_items, start=1):
        ranked_final.append(
            EvaluatedAlternative(
                alternative=item.alternative,
                rank=rank_idx,
                is_feasible=True,
                contribution_margin=item.contribution_margin,
                break_even_units=item.break_even_units,
                monthly_revenue=item.monthly_revenue,
                monthly_total_cost=item.monthly_total_cost,
                monthly_net_cash_flow=item.monthly_net_cash_flow,
                annual_roi_percent=item.annual_roi_percent,
                constraint_violations=(),
                assumption_labels=item.assumption_labels,
                followup_tasks=item.followup_tasks,
            )
        )

    infeasible_final: list[EvaluatedAlternative] = []
    for item in infeasible_items:
        infeasible_final.append(
            EvaluatedAlternative(
                alternative=item.alternative,
                rank=-1,
                is_feasible=False,
                contribution_margin=item.contribution_margin,
                break_even_units=item.break_even_units,
                monthly_revenue=item.monthly_revenue,
                monthly_total_cost=item.monthly_total_cost,
                monthly_net_cash_flow=item.monthly_net_cash_flow,
                annual_roi_percent=item.annual_roi_percent,
                constraint_violations=item.constraint_violations,
                assumption_labels=item.assumption_labels,
                followup_tasks=item.followup_tasks,
            )
        )

    best = ranked_final[0] if ranked_final else None

    return OptimizationResult(
        objective=objective,
        total_candidates=len(candidates),
        ranked_alternatives=tuple(ranked_final),
        infeasible_alternatives=tuple(infeasible_final),
        recommended_alternative=best,
        generated_followup_tasks=tuple(all_followups),
        as_of=datetime.now(timezone.utc).isoformat(),
    )
