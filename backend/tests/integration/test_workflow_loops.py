import uuid

import pytest
from backend.arthlens.demand.allocator import AllocationParameters, DemandZone, Facility
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.finance.loans import MoratoriumInterestTreatment, SubsidyTreatment
from backend.arthlens.geo.road_graph import RoadEdge, RoadGraph, RoadNode, RoadSpeedScenario
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.policy.rules import TruthValue
from backend.arthlens.workflows import (
    SpatialDemandInputs,
    run_loop_a_spatial_siting,
    run_loop_b_corridor_accessibility,
    run_loop_c_scheme_viability,
)


@pytest.mark.integration
def test_loop_a_returns_insufficient_data_without_traceable_allocation_inputs():
    ledger = Ledger()
    result = run_loop_a_spatial_siting(
        ledger,
        geo_unit_id="in:district:120",
        enterprise_id="proposed_store_1",
        allocator_type="huff",
    )

    assert result.status == "INSUFFICIENT_DATA"
    assert result.captured_demand_inr_monthly is None
    assert result.quantities == ()
    assert "registered zone demand quantities" in result.missing_evidence


@pytest.mark.integration
def test_loop_a_registers_only_outputs_with_complete_traceable_inputs():
    ledger = Ledger()
    quantities = (
        Quantity(
            "q_zone",
            "demand.zone.monthly",
            100.0,
            "INR/month",
            Kind.USER_ASSUMED,
            3,
            "in:district:120",
            2,
            "2026-11-08",
            source_refs=(("user", "scenario", "2026-11-08"),),
        ),
        Quantity(
            "q_candidate",
            "facility.attractiveness",
            2.0,
            "dimensionless",
            Kind.USER_ASSUMED,
            3,
            "in:district:120",
            5,
            "2026-11-08",
            source_refs=(("user", "scenario", "2026-11-08"),),
        ),
        Quantity(
            "q_competitor",
            "facility.attractiveness",
            1.0,
            "dimensionless",
            Kind.OBSERVED,
            4,
            "in:district:120",
            5,
            "2026-11-08",
            source_refs=(("DS-04", "node/1", "2026-11-08"),),
        ),
        Quantity(
            "q_candidate_time",
            "travel_time.minutes",
            5.0,
            "minute",
            Kind.CALCULATED,
            3,
            "in:district:120",
            2,
            "2026-11-08",
            parent_ids=("q_zone",),
        ),
        Quantity(
            "q_competitor_time",
            "travel_time.minutes",
            10.0,
            "minute",
            Kind.CALCULATED,
            3,
            "in:district:120",
            2,
            "2026-11-08",
            parent_ids=("q_zone",),
        ),
        Quantity(
            "q_lambda",
            "demand.huff.lambda",
            1.0,
            "dimensionless",
            Kind.SCENARIO,
            1,
            "in:district:120",
            2,
            "2026-11-08",
            source_refs=(("user", "scenario", "2026-11-08"),),
        ),
    )
    for quantity in quantities:
        ledger.register(quantity)

    result = run_loop_a_spatial_siting(
        ledger,
        geo_unit_id="in:district:120",
        enterprise_id="candidate",
        allocator_type="huff",
        allocation_inputs=SpatialDemandInputs(
            zones=(DemandZone("zone", 100.0),),
            facilities=(Facility("candidate", 2.0), Facility("competitor", 1.0)),
            parameters=AllocationParameters(
                {("zone", "candidate"): 5.0, ("zone", "competitor"): 10.0},
                distance_decay_exponent=1.0,
            ),
            provenance_by_input={
                "zone_demand:zone": "q_zone",
                "facility_attractiveness:candidate": "q_candidate",
                "facility_attractiveness:competitor": "q_competitor",
                "travel_time:zone:candidate": "q_candidate_time",
                "travel_time:zone:competitor": "q_competitor_time",
                "distance_decay_exponent": "q_lambda",
            },
        ),
    )

    assert result.status == "COMPLETED"
    assert result.captured_demand_inr_monthly is not None
    assert 0.0 < result.market_share_fraction < 1.0
    assert result.total_market_demand_inr == 100.0
    demand_q = ledger.get(result.quantities[0].id)
    assert demand_q.definition_key == "demand.monthly"
    assert demand_q.kind == Kind.ESTIMATED
    assert set(demand_q.parent_ids) == {quantity.id for quantity in quantities}


@pytest.mark.integration
def test_loop_b_returns_insufficient_data_without_source_versioned_inputs():
    result = run_loop_b_corridor_accessibility(Ledger())

    assert result.status == "INSUFFICIENT_DATA"
    assert result.analysis is None
    assert "source-versioned local road graph" in result.missing_evidence
    assert "explicit road-speed scenario" in result.missing_evidence


@pytest.mark.integration
def test_loop_b_corridor_accessibility_computes_catchments_from_traceable_inputs():
    ledger = Ledger()
    parents = (
        Quantity(
            "q_site",
            "site.location",
            1.0,
            "dimensionless",
            Kind.USER_ASSUMED,
            3,
            "in:district:120",
            2,
            "2026-11-08",
            source_refs=(("user", "scenario", "2026-11-08"),),
        ),
        Quantity(
            "q_speed",
            "routing.speed.residential",
            30.0,
            "km/hour",
            Kind.SCENARIO,
            1,
            "in:district:120",
            2,
            "2026-11-08",
            source_refs=(("user", "routing-speed-scenario", "2026-11-08"),),
        ),
    )
    for parent in parents:
        ledger.register(parent)
    graph = RoadGraph(
        nodes={
            "a": RoadNode("a", 81.8460, 25.4355, "DS-04:test:osm:node:a"),
            "b": RoadNode("b", 81.8490, 25.4380, "DS-04:test:osm:node:b"),
        },
        edges=(
            RoadEdge("ab", "a", "b", 420.0, "residential", "DS-04:test:osm:way:1"),
            RoadEdge("ba", "b", "a", 420.0, "residential", "DS-04:test:osm:way:1"),
        ),
        source_version_ids=frozenset(("DS-04:test",)),
    )
    result = run_loop_b_corridor_accessibility(
        ledger,
        graph=graph,
        site_coordinate=(81.8463, 25.4358),
        thresholds_minutes=(15.0, 30.0),
        site_geo_unit_id="in:district:120",
        speed_scenario=RoadSpeedScenario("user:routing-speeds", {"residential": 30.0}),
        corridor_width_m=200.0,
        parent_quantities=parents,
        as_of="2026-11-08",
        model_version="test-routing-v1",
    )

    assert result.status == "COMPLETED"
    assert result.snapped_node_id in ("a", "b")
    assert result.snap_distance_m is not None and result.snap_distance_m >= 0.0
    assert result.analysis is not None
    assert len(result.analysis.catchments) == 2
    assert len(result.registered_quantity_ids) > 0
    for def_key, q_id in result.registered_quantity_ids.items():
        quantity = ledger.get(q_id)
        assert quantity.definition_key == def_key
        assert quantity.geo_unit_id == "in:district:120"


@pytest.mark.integration
def test_loop_c_scheme_viability_builds_verified_report():
    ledger = Ledger()
    owner_id = str(uuid.uuid4())
    months = 39
    result = run_loop_c_scheme_viability(
        ledger,
        owner_id=owner_id,
        geo_unit_id="in:district:120",
        resolution=ResolutionTier.DISTRICT,
        project_cost_inr=500000.0,
        promoter_contribution_fraction=0.10,
        subsidy_fraction=0.25,
        annual_interest_rate=0.09,
        loan_term_months=36,
        moratorium_months=3,
        moratorium_interest_treatment=MoratoriumInterestTreatment.CAPITALISED,
        subsidy_treatment=SubsidyTreatment.BACK_ENDED_RELEASE,
        subsidy_release_month=6,
        unit_price=150.0,
        unit_variable_cost=60.0,
        fixed_operating_costs_monthly=25000.0,
        monthly_sales_units=1200.0,
        monthly_growth_rate=0.01,
        seasonality_factors=(1.0,),
        taxes_by_month=(0.0,) * months,
        other_payments_by_month=(0.0,) * months,
        working_capital_need_by_month=(25000.0,) * months,
        opening_working_capital_need=25000.0,
        days_inventory=20.0,
        days_receivable=15.0,
        days_payable=30.0,
    )

    assert result.scheme_eligibility_status == TruthValue.UNKNOWN
    assert result.calculation_provenance["eligibility"]["status"] == "RULE_UNAVAILABLE"
    assert result.calculation_provenance["eligibility"]["official_award_decision"] is False
    assert "approved policy rule/version and evidence are required" in result.verified_report.rendered_text
    assert result.break_even_quantity > 0
    # Price 150, VC 60 -> CM 90. Fixed 25000 -> 25000/90 ~ 277.78 units
    assert 270 < result.break_even_quantity < 285

    assert result.verified_report.rendered_text is not None
    assert len(result.verified_report.quantity_records) == 2
    break_even_quantity, dscr_quantity = result.quantities
    assert dscr_quantity.value == result.projection_summary.minimum_dscr
    assert break_even_quantity.id not in dscr_quantity.parent_ids
    assert set(result.calculation_provenance["loan_schedule_debt_service_quantity_ids"]).issubset(
        set(dscr_quantity.parent_ids)
    )
    assert result.calculation_provenance["parameters"]["subsidy_treatment"] == "BACK_ENDED_RELEASE"
    assert ledger.get(result.calculation_provenance["input_quantity_ids"]["monthly_growth_rate"]).value == 0.01

    # Verify JSON export
    assert '"schema_version":1' in result.report_json
    assert '"finance.break_even_quantity"' in result.report_json

    # Verify CSV export
    assert "record_type,rendered_text" in result.report_csv
    assert "finance.break_even_quantity" in result.report_csv
