import pytest
from backend.arthlens.agent.execution import (
    ToolApprovalRequired,
    ToolExecutionRegistry,
    build_default_tool_executor,
)
from backend.arthlens.agent.tool_registry import (
    FetchEconomicIndicatorInput,
    ToolSchema,
    ToolSchemaRegistry,
    build_default_tool_registry,
)
from backend.arthlens.agent.worker import (
    build_production_tool_executor,
    default_production_verifier,
)
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.in_memory import InMemoryQuantityRepository


@pytest.mark.unit
def test_default_executor_runs_only_bound_break_even_tool():
    executor = build_default_tool_executor()

    assert executor.execute(
        "calculate_break_even",
        {"price": 100, "variable_cost": 40, "fixed_costs": 300},
    ) == {"break_even_quantity": 5, "quality_flags": []}
    assert executor.execute(
        "calculate_break_even",
        {"price": 40, "variable_cost": 40, "fixed_costs": 300},
    ) == {
        "break_even_quantity": None,
        "quality_flags": ["NO_BREAK_EVEN"],
    }
    with pytest.raises(KeyError, match="no executable handler"):
        executor.execute(
            "fetch_economic_indicator",
            {"source": "data.gov.in", "geo_id": "IN-X", "series": "price"},
        )


@pytest.mark.unit
def test_default_executor_runs_explicit_generic_loan_schedule():
    executor = build_default_tool_executor()

    schedule = executor.execute(
        "calculate_loan_schedule",
        {
            "principal": 1200,
            "rate": 0,
            "term": 3,
            "moratorium": {
                "months": 0,
                "interest_treatment": "PAID",
            },
            "subsidy_params": {
                "amount": 0,
                "treatment": "ADJUSTS_PRINCIPAL",
                "release_month": None,
            },
        },
    )

    assert schedule["financed_principal"] == 1200
    assert schedule["total_repaid"] == 1200
    assert [row["debt_service"] for row in schedule["rows"]] == [400, 400, 400]
    assert schedule["rows"][-1]["closing_balance"] == 0


@pytest.mark.unit
def test_loan_schedule_tool_requires_explicit_treatments_and_rejects_unknown_fields():
    executor = build_default_tool_executor()
    payload = {
        "principal": 1200,
        "rate": 0,
        "term": 3,
        "moratorium": {"months": 0, "interest_treatment": "PAID"},
        "subsidy_params": {
            "amount": 0,
            "treatment": "ADJUSTS_PRINCIPAL",
            "release_month": None,
        },
    }

    with pytest.raises(ValueError):
        executor.execute(
            "calculate_loan_schedule",
            {**payload, "subsidy_params": {"amount": 0, "treatment": "UNKNOWN"}},
        )
    with pytest.raises(ValueError):
        executor.execute(
            "calculate_loan_schedule",
            {
                **payload,
                "subsidy_params": {
                    **payload["subsidy_params"],
                    "assumed_rate": 0,
                },
            },
        )


@pytest.mark.unit
def test_executor_validates_input_before_invoking_handler():
    calls = []
    schemas = ToolSchemaRegistry()
    schemas.register(ToolSchema("sample", FetchEconomicIndicatorInput, "sample result"))
    executor = ToolExecutionRegistry(
        schemas,
        {"sample": lambda payload: calls.append(payload)},
    )

    with pytest.raises(ValueError):
        executor.execute("sample", {"source": "", "geo_id": "IN-X", "series": "price"})
    assert calls == []


@pytest.mark.unit
def test_executor_fails_closed_for_approval_required_tool():
    calls = []
    schemas = ToolSchemaRegistry()
    schemas.register(
        ToolSchema(
            "publish",
            FetchEconomicIndicatorInput,
            "published result",
            approval_required=True,
        )
    )
    executor = ToolExecutionRegistry(
        schemas,
        {"publish": lambda payload: calls.append(payload)},
    )
    payload = {"source": "data.gov.in", "geo_id": "IN-X", "series": "price"}

    with pytest.raises(ToolApprovalRequired, match="requires explicit approval"):
        executor.execute("publish", payload)
    assert calls == []

    approved_executor = ToolExecutionRegistry(
        schemas,
        {"publish": lambda payload: {"published": payload.source == "data.gov.in"}},
        approval_check=lambda tool, parsed: (
            tool.name == "publish" and isinstance(parsed, FetchEconomicIndicatorInput)
        ),
    )
    assert approved_executor.execute("publish", payload) == {"published": True}


@pytest.mark.unit
def test_executor_rejects_non_json_results_and_unknown_bindings():
    schemas = ToolSchemaRegistry()
    schemas.register(ToolSchema("sample", FetchEconomicIndicatorInput, "sample result"))
    payload = {"source": "data.gov.in", "geo_id": "IN-X", "series": "price"}
    executor = ToolExecutionRegistry(
        schemas,
        {"sample": lambda parsed: float("inf") if parsed.source else 0},
    )

    with pytest.raises(TypeError, match="non-JSON-compatible"):
        executor.execute("sample", payload)
    with pytest.raises(KeyError, match="not registered"):
        ToolExecutionRegistry(schemas, {"missing": lambda parsed: parsed.source})


@pytest.mark.unit
def test_executor_validates_declared_output_contract():
    schemas = build_default_tool_registry()
    invalid_executor = ToolExecutionRegistry(
        schemas,
        {"calculate_break_even": lambda payload: {"unexpected": True}},
    )

    with pytest.raises(ValueError):
        invalid_executor.execute(
            "calculate_break_even",
            {"price": 100, "variable_cost": 40, "fixed_costs": 300},
        )


@pytest.mark.unit
def test_spatial_demand_tool_returns_insufficient_data_for_missing_route_evidence():
    executor = build_production_tool_executor(InMemoryQuantityRepository())

    result = executor.execute(
        "allocate_spatial_demand",
        {
            "zones": [{"id": "zone-1", "demand": 100}],
            "facilities": [{"id": "candidate", "attractiveness": 1}],
            "allocator": "huff",
            "params": {},
            "seed": 1,
        },
    )

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["allocated_shares"] == {}
    assert any("ledger provenance for zone demand" in item for item in result["missing_evidence"])
    assert any("route-derived travel times" in item for item in result["missing_evidence"])
    assert any("distance-decay" in item for item in result["missing_evidence"])


def _quantity(quantity_id: str, definition_key: str, value: float) -> Quantity:
    return Quantity(
        id=quantity_id,
        definition_key=definition_key,
        value=value,
        unit="dimensionless",
        kind=Kind.USER_ASSUMED,
        evidence_floor=3,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-11-08",
        source_refs=(("user", "scenario", "2026-11-08"),),
    )


def _valid_spatial_payload() -> dict:
    return {
        "zones": [{"id": "zone-1", "demand": 100.0}],
        "facilities": [{"id": "candidate", "attractiveness": 2.0}],
        "allocator": "huff",
        "params": {
            "travel_time_minutes_by_pair": {"zone-1,candidate": 5.0},
            "distance_decay_exponent": 1.5,
        },
        "seed": 1,
        "provenance": {
            "zone_demand_quantity_ids": {"zone-1": "q-zone"},
            "facility_attractiveness_quantity_ids": {"candidate": "q-facility"},
            "travel_time_quantity_ids": [
                {"zone_id": "zone-1", "facility_id": "candidate", "quantity_id": "q-travel"}
            ],
            "distance_decay_quantity_id": "q-lambda",
        },
    }


def _spatial_executor() -> tuple[ToolExecutionRegistry, InMemoryQuantityRepository]:
    repository = InMemoryQuantityRepository()
    for quantity in (
        _quantity("q-zone", "demand.zone.monthly", 100.0),
        _quantity("q-facility", "facility.attractiveness", 2.0),
        _quantity("q-travel", "travel_time.minutes", 5.0),
        _quantity("q-lambda", "demand.huff.lambda", 1.5),
    ):
        repository.save(quantity)
    return build_production_tool_executor(repository), repository


@pytest.mark.unit
def test_spatial_demand_tool_accepts_complete_matching_provenance():
    executor, _ = _spatial_executor()

    result = executor.execute("allocate_spatial_demand", _valid_spatial_payload())

    assert result["status"] == "COMPLETED"
    assert result["allocated_shares"] == {"candidate": 100.0}
    assert result["input_quantity_ids"] == ["q-zone", "q-facility", "q-travel", "q-lambda"]


@pytest.mark.unit
def test_spatial_demand_tool_rejects_unknown_or_unrelated_provenance_ids():
    executor, repository = _spatial_executor()
    unknown_payload = _valid_spatial_payload()
    unknown_payload["provenance"]["zone_demand_quantity_ids"]["zone-1"] = "missing"

    unknown = executor.execute("allocate_spatial_demand", unknown_payload)
    assert unknown["status"] == "INSUFFICIENT_DATA"
    assert any("unknown ledger quantity missing" in item for item in unknown["missing_evidence"])

    repository.save(_quantity("q-unrelated", "population.total", 100.0))
    unrelated_payload = _valid_spatial_payload()
    unrelated_payload["provenance"]["zone_demand_quantity_ids"]["zone-1"] = "q-unrelated"

    unrelated = executor.execute("allocate_spatial_demand", unrelated_payload)
    assert unrelated["status"] == "INSUFFICIENT_DATA"
    assert any(
        "unrelated ledger quantity q-unrelated" in item for item in unrelated["missing_evidence"]
    )


@pytest.mark.unit
def test_spatial_demand_tool_rejects_missing_or_value_mismatched_provenance():
    executor, repository = _spatial_executor()
    missing_payload = _valid_spatial_payload()
    del missing_payload["provenance"]["facility_attractiveness_quantity_ids"]["candidate"]

    missing = executor.execute("allocate_spatial_demand", missing_payload)
    assert missing["status"] == "INSUFFICIENT_DATA"
    assert any("facility attractiveness candidate" in item for item in missing["missing_evidence"])

    repository.save(_quantity("q-mismatched", "travel_time.minutes", 6.0))
    mismatched_payload = _valid_spatial_payload()
    mismatched_payload["provenance"]["travel_time_quantity_ids"][0]["quantity_id"] = "q-mismatched"

    mismatched = executor.execute("allocate_spatial_demand", mismatched_payload)
    assert mismatched["status"] == "INSUFFICIENT_DATA"
    assert any("does not match travel time" in item for item in mismatched["missing_evidence"])


@pytest.mark.unit
def test_sensitivity_tool_returns_insufficient_data_without_explicit_linked_inputs():
    executor = build_production_tool_executor(InMemoryQuantityRepository())

    result = executor.execute(
        "run_sensitivity_analysis",
        {"scenario": {}, "inputs": {}},
    )

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["baseline_outputs"] == {}
    assert result["points"] == []
    assert result["missing_evidence"]


@pytest.mark.unit
def test_production_verifier_rejects_empty_insufficient_and_mismatched_results():
    tool_input = {"price": 100, "variable_cost": 40, "fixed_costs": 300}

    assert not default_production_verifier({}, ())
    assert not default_production_verifier({}, ({
        "step_id": "allocation",
        "tool_name": "allocate_spatial_demand",
        "tool_input": {},
        "result": {"status": "INSUFFICIENT_DATA", "missing_evidence": ["travel times"]},
    },))
    assert not default_production_verifier({}, ({
        "step_id": "break_even",
        "tool_name": "calculate_break_even",
        "tool_input": tool_input,
        "result": {"break_even_quantity": 999.0, "quality_flags": []},
    },))


@pytest.mark.unit
def test_production_verifier_accepts_recomputed_deterministic_result():
    tool_input = {"price": 100, "variable_cost": 40, "fixed_costs": 300}
    executor = build_default_tool_executor()
    result = executor.execute("calculate_break_even", tool_input)

    assert default_production_verifier({}, ({
        "step_id": "break_even",
        "tool_name": "calculate_break_even",
        "tool_input": tool_input,
        "result": result,
    },))


@pytest.mark.unit
def test_fetch_economic_indicator_tool_returns_quantities_or_insufficient():
    repo = InMemoryQuantityRepository()
    repo.save(Quantity(
        id="q-pop",
        definition_key="population.total",
        value=150000.0,
        unit="person",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-11-08",
        source_refs=(("DS-01", "census/table1", "2026-11-08"),),
    ))
    executor = build_production_tool_executor(quantity_repository=repo)

    found = executor.execute("fetch_economic_indicator", {
        "source": "DS-01",
        "geo_id": "in:district:120",
        "series": "population.total",
    })
    assert found["status"] == "COMPLETED"
    assert len(found["quantities"]) == 1
    assert found["quantities"][0]["value"] == 150000.0

    not_found = executor.execute("fetch_economic_indicator", {
        "source": "DS-01",
        "geo_id": "in:district:999",
        "series": "population.total",
    })
    assert not_found["status"] == "INSUFFICIENT_DATA"
    assert not_found["quantities"] == []
    assert not_found["missing_evidence"]


@pytest.mark.unit
def test_verify_claim_tool_verifies_authoritative_quantities():
    repo = InMemoryQuantityRepository()
    repo.save(Quantity(
        id="q-emp",
        definition_key="employment.rate",
        value=65.5,
        unit="percent",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-11-08",
        source_refs=(("DS-02", "table/emp", "2026-11-08"),),
    ))
    executor = build_production_tool_executor(quantity_repository=repo)

    verified = executor.execute("verify_claim", {"claim": "q-emp"})
    assert verified["status"] == "COMPLETED"
    assert verified["verdict"] == "VERIFIED"
    assert len(verified["evidence"]) == 1

    unverified = executor.execute("verify_claim", {"claim": "unregistered claim fact"})
    assert unverified["status"] == "INSUFFICIENT_DATA"
    assert unverified["verdict"] == "UNVERIFIED"
    assert unverified["missing_evidence"]


@pytest.mark.unit
def test_search_policy_and_evaluate_eligibility_tools():
    from backend.arthlens.infra.in_memory import InMemoryPolicyRuleRepository
    policy_repo = InMemoryPolicyRuleRepository()
    doc_id = policy_repo.save_document({
        "id": "doc-1",
        "scheme_id": "PMEGP",
        "source_version_id": "v1",
        "document_url": "https://msme.gov.in/pmegp.pdf",
        "sha256": "0" * 64,
    })
    rule_data = {
        "id": "rule-1",
        "scheme_id": "PMEGP",
        "rule_key": "pmegp.manufacturing.cap",
        "version": 1,
        "rule_ast": {
            "type": "predicate",
            "fact": "project_cost",
            "comparison": "lte",
            "expected": 5000000.0,
        },
        "evidence_requirements": {
            "project_cost": {
                "definition_key": "finance.project_cost",
                "unit": "INR",
                "allowed_kinds": ["USER_ASSUMED", "OBSERVED"],
                "minimum_evidence_floor": 2,
            }
        },
        "source_references": [
            {
                "document_id": doc_id,
                "source_version_id": "v1",
                "document_url": "https://msme.gov.in/pmegp.pdf",
                "sha256": "0" * 64,
                "locator": "Clause 4.1",
            }
        ],
        "effective_from": "2026-01-01",
        "status": "APPROVED",
    }
    policy_repo.save_rule(rule_data)
    executor = build_production_tool_executor(policy_repository=policy_repo)

    search_result = executor.execute("search_policy_documents", {
        "scheme": "PMEGP",
        "query": "manufacturing",
    })
    assert search_result["status"] == "COMPLETED"
    assert len(search_result["passages"]) >= 1

    # Eligible
    eval_eligible = executor.execute("evaluate_scheme_eligibility", {
        "scheme": "PMEGP",
        "facts": {"project_cost": 2500000.0},
        "as_of": "2026-11-08",
    })
    assert eval_eligible["status"] == "COMPLETED"
    assert eval_eligible["eligibility"] == "ELIGIBLE"

    # Ineligible
    eval_ineligible = executor.execute("evaluate_scheme_eligibility", {
        "scheme": "PMEGP",
        "facts": {"project_cost": 7500000.0},
        "as_of": "2026-11-08",
    })
    assert eval_ineligible["status"] == "COMPLETED"
    assert eval_ineligible["eligibility"] == "INELIGIBLE"

    # Unknown fact
    eval_unknown = executor.execute("evaluate_scheme_eligibility", {
        "scheme": "PMEGP",
        "facts": {},
        "as_of": "2026-11-08",
    })
    assert eval_unknown["status"] == "INSUFFICIENT_DATA"
    assert "project_cost" in eval_unknown["missing_evidence"][0]

    # Unapproved candidate scheme rules fail closed with UNKNOWN and disclaimer
    eval_unapproved = executor.execute("evaluate_scheme_eligibility", {
        "scheme": "PMFME",
        "facts": {"enterprise.sector": "food_processing", "applicant.age": 25},
        "as_of": "2026-11-08",
    })
    assert eval_unapproved["status"] == "UNAPPROVED_CANDIDATE_RULE"
    assert eval_unapproved["eligibility"] == "UNKNOWN"
    assert "HUMAN_REVIEW_REQUIRED" in eval_unapproved["disclaimer"]
    assert any("Gate 2" in item for item in eval_unapproved["missing_evidence"])


@pytest.mark.unit
def test_run_business_scenario_tool_executes_projection():
    executor = build_production_tool_executor()
    scenario_input = {
        "initial_quantity": 100.0,
        "monthly_growth_rate": 0.05,
        "seasonality_factors": [1.0] * 12,
        "price_per_unit_by_month": [50.0] * 12,
        "variable_cost_per_unit_by_month": [20.0] * 12,
        "operating_expenses_by_month": [1000.0] * 12,
        "debt_service_by_month": [500.0] * 12,
        "taxes_by_month": [200.0] * 12,
        "other_payments_by_month": [0.0] * 12,
        "subsidy_cash_release_by_month": [0.0] * 12,
        "working_capital_need_by_month": [2000.0] * 12,
        "opening_working_capital_need": 1500.0,
        "equity": 50000.0,
        "disbursed_loan": 100000.0,
        "capex": 120000.0,
        "days_inventory": 30.0,
        "days_receivable": 30.0,
        "days_payable": 30.0,
    }
    result = executor.execute("run_business_scenario", {"scenario": scenario_input})
    assert result["status"] == "COMPLETED"
    assert result["total_revenue"] > 0
    assert result["months"] == 12

    # Incomplete scenario
    incomplete = executor.execute("run_business_scenario", {"scenario": {"initial_quantity": 100.0}})
    assert incomplete["status"] == "INSUFFICIENT_DATA"
    assert incomplete["missing_evidence"]


@pytest.mark.unit
def test_generate_report_and_compare_scenarios():
    from backend.arthlens.infra.in_memory import InMemoryScenarioRepository
    scenario_repo = InMemoryScenarioRepository()
    scenario_repo.save_scenario({
        "id": "sc-1",
        "name": "Scenario 1",
        "owner_id": "user-1",
        "break_even_units": 100.0,
        "monthly_emi": 1500.0,
        "total_interest": 5000.0,
        "viability_status": "FEASIBLE",
    })
    scenario_repo.save_scenario({
        "id": "sc-2",
        "name": "Scenario 2",
        "owner_id": "user-1",
        "break_even_units": 150.0,
        "monthly_emi": 2200.0,
        "total_interest": 8000.0,
        "viability_status": "FEASIBLE",
    })
    executor = build_production_tool_executor(scenario_repository=scenario_repo)

    comparison = executor.execute("compare_scenarios", {"run_ids": ["sc-1", "sc-2"]})
    assert comparison["status"] == "COMPLETED"
    assert comparison["compared_count"] == 2
    assert "sc-1" in comparison["comparison_matrix"]
    assert "sc-2" in comparison["comparison_matrix"]

    report = executor.execute("generate_report", {
        "verified_claim_graph": {
            "title": "Varanasi Logistics Expansion",
            "summary": "Feasibility verified across population and road network",
            "claims": [{"claim": "demand.sufficient", "verdict": "VERIFIED"}],
        }
    })
    assert report["status"] == "COMPLETED"
    assert report["report_id"]
    assert report["title"] == "Varanasi Logistics Expansion"


@pytest.mark.unit
def test_compute_catchment_tool():
    from backend.arthlens.geo.road_graph import RoadEdge, RoadGraph, RoadNode
    graph = RoadGraph(
        nodes={
            "n1": RoadNode("n1", 81.8460, 25.4355, "DS-04:node:1"),
            "n2": RoadNode("n2", 81.8490, 25.4380, "DS-04:node:2"),
        },
        edges=(
            RoadEdge("e1", "n1", "n2", 300.0, "residential", "DS-04:way:1"),
            RoadEdge("e2", "n2", "n1", 300.0, "residential", "DS-04:way:1"),
        ),
        source_version_ids=frozenset(("DS-04:v1",)),
    )
    executor = build_production_tool_executor()

    result = executor.execute("compute_catchment", {
        "site": {
            "longitude": 81.8465,
            "latitude": 25.4360,
            "graph": graph,
            "speeds": {"residential": 30.0},
            "corridor_width_m": 200.0,
        },
        "minutes": 15.0,
        "mode": "driving",
    })
    assert result["status"] == "COMPLETED"
    assert result["nodes_reached"] >= 1
    assert "geometry" in result

    # Missing coordinates returns INSUFFICIENT_DATA
    missing = executor.execute("compute_catchment", {
        "site": {},
        "minutes": 15.0,
        "mode": "driving",
    })
    assert missing["status"] == "INSUFFICIENT_DATA"
    assert missing["missing_evidence"]


@pytest.mark.unit
def test_publish_to_shared_view_requires_approval_and_generates_token():
    from backend.arthlens.agent.execution import ToolApprovalRequired

    class MockRunRepo:
        def get_run(self, run_id):
            return {"id": run_id, "state": "COMPLETED"} if run_id == "run-123" else None

    executor = build_production_tool_executor(agent_run_repository=MockRunRepo())

    # Without approval check, raises ToolApprovalRequired
    with pytest.raises(ToolApprovalRequired):
        executor.execute("publish_to_shared_view", {"run_id": "run-123"})

    # With approved check
    approved_executor = build_production_tool_executor(
        agent_run_repository=MockRunRepo(),
        approval_check=lambda tool, parsed: True,
    )
    res = approved_executor.execute("publish_to_shared_view", {"run_id": "run-123"})
    assert res["status"] == "COMPLETED"
    assert res["run_id"] == "run-123"
    assert "share_token" in res
    assert "/shared/view/run-123" in res["shared_view_url"]

    # Nonexistent run returns INSUFFICIENT_DATA
    missing_run = approved_executor.execute("publish_to_shared_view", {"run_id": "run-missing"})
    assert missing_run["status"] == "INSUFFICIENT_DATA"
    assert missing_run["missing_evidence"]


@pytest.mark.unit
def test_durable_worker_loop_claims_and_recovers():
    import threading
    from backend.arthlens.agent.orchestration import OrchestrationResult
    from backend.arthlens.agent.run_lifecycle import AgentRunState
    from backend.arthlens.agent.worker import run_worker_loop

    class FakeRepo:
        def __init__(self):
            self.recovered_count = 0
            self.claimed = [{"id": "run-worker-test", "state": "CREATED"}]

        def recover_stale_runs(self, timeout_seconds=300):
            self.recovered_count += 1
            return 1

        def claim_pending_run(self):
            if self.claimed:
                return self.claimed.pop(0)
            return None

    class FakeOrch:
        def __init__(self):
            self.runs = []

        def run(self, run_id):
            self.runs.append(run_id)
            return OrchestrationResult(AgentRunState.COMPLETED, "Completed successfully")

    repo = FakeRepo()
    orch = FakeOrch()
    stop_event = threading.Event()

    processed = run_worker_loop(
        poll_interval=0.01,
        stop_event=stop_event,
        max_iterations=2,
        orchestrator=orch,
        repository=repo,
    )
    assert processed == 1
    assert orch.runs == ["run-worker-test"]
    assert repo.recovered_count >= 1



