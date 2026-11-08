"""Unit tests for discrete alternative strategy and site enumeration optimizer."""

import pytest
from backend.arthlens.optimization import (
    CandidateAlternative,
    OptimizationObjective,
    enumerate_and_rank_alternatives,
)


@pytest.mark.unit
def test_enumerator_empty_candidates():
    res = enumerate_and_rank_alternatives([])
    assert res.total_candidates == 0
    assert len(res.ranked_alternatives) == 0
    assert res.recommended_alternative is None


@pytest.mark.unit
def test_enumerator_ranks_alternatives_by_net_cash_flow():
    c1 = CandidateAlternative(
        id="site_naini",
        name="Naini Industrial Area",
        capital_expenditure=200000.0,
        price_per_unit=150.0,
        variable_cost_per_unit=90.0,
        fixed_costs_per_month=30000.0,
        target_monthly_volume=800.0,
        site_coordinate=(25.385, 81.875),
        is_osm_suggestion=True,
        zoning_verified=False,
    )
    c2 = CandidateAlternative(
        id="site_civil_lines",
        name="Civil Lines Commercial",
        capital_expenditure=350000.0,
        price_per_unit=180.0,
        variable_cost_per_unit=100.0,
        fixed_costs_per_month=50000.0,
        target_monthly_volume=1200.0,
        site_coordinate=(25.452, 81.834),
        is_osm_suggestion=False,
        zoning_verified=True,
    )

    res = enumerate_and_rank_alternatives(
        [c1, c2],
        objective=OptimizationObjective.MAXIMIZE_NET_CASH_FLOW,
    )

    assert res.total_candidates == 2
    assert len(res.ranked_alternatives) == 2
    assert len(res.infeasible_alternatives) == 0

    # Net cash flow:
    # c1: 800 * (150 - 90) - 30000 = 800 * 60 - 30000 = 48000 - 30000 = 18000
    # c2: 1200 * (180 - 100) - 50000 = 1200 * 80 - 50000 = 96000 - 50000 = 46000
    assert res.ranked_alternatives[0].alternative.id == "site_civil_lines"
    assert res.ranked_alternatives[0].rank == 1
    assert res.ranked_alternatives[0].monthly_net_cash_flow == 46000.0

    assert res.ranked_alternatives[1].alternative.id == "site_naini"
    assert res.ranked_alternatives[1].rank == 2
    assert res.ranked_alternatives[1].monthly_net_cash_flow == 18000.0

    # Check caveat and follow-up generation for OSM suggestion
    naini_item = res.ranked_alternatives[1]
    assert any("Caveat: Site not checked" in label for label in naini_item.assumption_labels)
    assert any("Verify municipal zoning" in task for task in naini_item.followup_tasks)


@pytest.mark.unit
def test_enumerator_filters_infeasible_budget_and_break_even():
    c1 = CandidateAlternative(
        id="site_expensive",
        name="Expensive Hub",
        capital_expenditure=500000.0,
        price_per_unit=100.0,
        variable_cost_per_unit=60.0,
        fixed_costs_per_month=20000.0,
        target_monthly_volume=1000.0,
    )
    c2 = CandidateAlternative(
        id="site_feasible",
        name="Budget Hub",
        capital_expenditure=250000.0,
        price_per_unit=120.0,
        variable_cost_per_unit=70.0,
        fixed_costs_per_month=15000.0,
        target_monthly_volume=800.0,
    )

    res = enumerate_and_rank_alternatives(
        [c1, c2],
        max_capital_budget=300000.0,
    )

    assert len(res.ranked_alternatives) == 1
    assert res.recommended_alternative.alternative.id == "site_feasible"
    assert len(res.infeasible_alternatives) == 1
    assert res.infeasible_alternatives[0].alternative.id == "site_expensive"
    assert any("exceeds budget" in v for v in res.infeasible_alternatives[0].constraint_violations)

