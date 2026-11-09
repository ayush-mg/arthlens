"""
Durable Agent Run Worker and Orchestration Engine.

Authoritative Reference: ArthLens Build Handbook v1.0 (Parts 8.2-8.5, 9.1, 14.4).
Phase: P4 (Agent Orchestration, Background Execution, and Lifecycle Telemetry).
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from functools import partial
from math import isclose, isfinite
from typing import Any, Mapping

from pydantic import BaseModel

from backend.arthlens.agent.budgets import RunBudgetLimits
from backend.arthlens.agent.execution import (
    ApprovalCheck,
    ToolExecutionRegistry,
    _calculate_break_even,
    _calculate_loan_schedule,
)
from backend.arthlens.agent.followups import tasks_from_unresolved_gaps
from backend.arthlens.agent.orchestration import AgentRunOrchestrator, OrchestrationResult
from backend.arthlens.agent.planning import GoalInterpreter, Planner, PlanValidator
from backend.arthlens.agent.run_lifecycle import AgentRunState
from backend.arthlens.agent.tool_registry import (
    AllocateSpatialDemandInput,
    CompareScenariosInput,
    ComputeCatchmentInput,
    CreateFollowupTasksInput,
    EvaluateSchemeEligibilityInput,
    FetchEconomicIndicatorInput,
    GenerateReportInput,
    PublishToSharedViewInput,
    RunBusinessScenarioInput,
    RunSensitivityAnalysisInput,
    SearchPolicyDocumentsInput,
    VerifyClaimInput,
    build_default_tool_registry,
)
from backend.arthlens.demand.allocator import (
    AllocationParameters,
    DemandZone,
    Facility,
    HuffAllocator,
    NearestFacilityAllocator,
)
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.repositories import (
    PolicyRuleRepository,
    QuantityRepository,
    ScenarioRepository,
)
from backend.arthlens.finance.projection import FinancialScenario, project_monthly_cash_flow
from backend.arthlens.geo.dijkstra import build_catchments
from backend.arthlens.geo.road_graph import RoadSpeedScenario
from backend.arthlens.geo.road_repository import PostgresRoadGraphRepository
from backend.arthlens.infra.repositories import (
    PostgresAgentRunRepository,
    PostgresFollowupTaskRepository,
    PostgresPolicyRuleRepository,
    PostgresQuantityRepository,
    PostgresScenarioRepository,
)
from backend.arthlens.llm import get_llm_client
from backend.arthlens.policy.rules import TruthValue
from backend.arthlens.policy.serialization import parse_rule_ast
from backend.arthlens.policy.visitors import EligibilityEvaluator
from backend.arthlens.simulation.sensitivity import run_one_at_a_time_sensitivity

logger = logging.getLogger(__name__)


def _allocate_spatial_demand_handler(
    payload: BaseModel,
    *,
    quantity_repository: QuantityRepository,
) -> dict[str, Any]:
    if not isinstance(payload, AllocateSpatialDemandInput):
        raise TypeError("allocate_spatial_demand received an unexpected input model.")

    zones = [DemandZone(id=z["id"], demand=float(z["demand"])) for z in payload.zones]
    facilities = [
        Facility(id=f["id"], attractiveness=float(f["attractiveness"])) for f in payload.facilities
    ]

    # Convert travel time pairs
    travel_times: dict[tuple[str, str], float] = {}
    raw_times = payload.params.get("travel_time_minutes_by_pair", {})
    if isinstance(raw_times, dict):
        for k, v in raw_times.items():
            if isinstance(k, (list, tuple)) and len(k) == 2:
                travel_times[(str(k[0]), str(k[1]))] = float(v)
            elif isinstance(k, str) and ":" in k:
                z_id, f_id = k.split(":", 1)
                travel_times[(z_id, f_id)] = float(v)
            elif isinstance(k, str) and "," in k:
                z_id, f_id = k.split(",", 1)
                travel_times[(z_id.strip(), f_id.strip())] = float(v)

    expected_pairs = {(z.id, f.id) for z in zones for f in facilities}
    missing_pairs = sorted(expected_pairs - set(travel_times))
    missing_evidence: list[str] = []
    provenance = payload.provenance
    zone_quantity_ids = provenance.zone_demand_quantity_ids
    facility_quantity_ids = provenance.facility_attractiveness_quantity_ids
    travel_quantity_ids = {
        (item.zone_id, item.facility_id): item.quantity_id
        for item in provenance.travel_time_quantity_ids
    }

    missing_evidence.extend(
        f"ledger provenance for zone demand {zone.id}"
        for zone in zones
        if zone.id not in zone_quantity_ids
    )
    missing_evidence.extend(
        f"ledger provenance for facility attractiveness {facility.id}"
        for facility in facilities
        if facility.id not in facility_quantity_ids
    )
    missing_evidence.extend(
        f"ledger provenance for travel time {zone_id}/{facility_id}"
        for zone_id, facility_id in sorted(expected_pairs - set(travel_quantity_ids))
    )
    unexpected_zone_ids = sorted(set(zone_quantity_ids) - {zone.id for zone in zones})
    unexpected_facility_ids = sorted(
        set(facility_quantity_ids) - {facility.id for facility in facilities}
    )
    unexpected_travel_pairs = sorted(set(travel_quantity_ids) - expected_pairs)
    missing_evidence.extend(
        f"unrelated zone-demand provenance mapping {zone_id}" for zone_id in unexpected_zone_ids
    )
    missing_evidence.extend(
        f"unrelated facility-attractiveness provenance mapping {facility_id}"
        for facility_id in unexpected_facility_ids
    )
    missing_evidence.extend(
        f"unrelated travel-time provenance mapping {zone_id}/{facility_id}"
        for zone_id, facility_id in unexpected_travel_pairs
    )
    if len(travel_quantity_ids) != len(provenance.travel_time_quantity_ids):
        missing_evidence.append("duplicate travel-time provenance mapping")
    if missing_pairs:
        missing_evidence.append(
            "route-derived travel times for "
            + ", ".join(f"{zone_id}/{facility_id}" for zone_id, facility_id in missing_pairs)
        )
    if (
        payload.allocator.lower() == "huff"
        and payload.params.get("distance_decay_exponent") is None
    ):
        missing_evidence.append("an explicit distance-decay scenario assumption")
    if payload.allocator.lower() == "huff" and not provenance.distance_decay_quantity_id:
        missing_evidence.append("ledger provenance for the distance-decay scenario assumption")
    if missing_evidence:
        return _insufficient_allocation_result(payload.allocator, missing_evidence)

    provenance_checks = [
        *(
            (
                zone_quantity_ids[zone.id],
                "demand.zone.monthly",
                zone.demand,
                f"zone demand {zone.id}",
            )
            for zone in zones
        ),
        *(
            (
                facility_quantity_ids[facility.id],
                "facility.attractiveness",
                facility.attractiveness,
                f"facility attractiveness {facility.id}",
            )
            for facility in facilities
        ),
        *(
            (
                travel_quantity_ids[(zone_id, facility_id)],
                "travel_time.minutes",
                travel_times[(zone_id, facility_id)],
                f"travel time {zone_id}/{facility_id}",
            )
            for zone_id, facility_id in sorted(expected_pairs)
        ),
    ]
    if payload.allocator.lower() == "huff":
        provenance_checks.append(
            (
                provenance.distance_decay_quantity_id,
                "demand.huff.lambda",
                payload.params["distance_decay_exponent"],
                "distance-decay scenario assumption",
            )
        )

    invalid_provenance = _validate_allocation_provenance(quantity_repository, provenance_checks)
    if invalid_provenance:
        return _insufficient_allocation_result(payload.allocator, invalid_provenance)

    alloc_params = AllocationParameters(
        travel_time_minutes_by_pair=travel_times,
        distance_decay_exponent=payload.params.get("distance_decay_exponent"),
    )

    if payload.allocator.lower() == "huff":
        allocator = HuffAllocator()
    else:
        allocator = NearestFacilityAllocator()

    result = allocator.allocate(zones, facilities, alloc_params)
    allocated_shares = {f.id: result.facility_demand.get(f.id, 0.0) for f in facilities}

    return {
        "status": "COMPLETED",
        "allocator": payload.allocator,
        "total_demand": sum(z.demand for z in zones),
        "allocated_shares": allocated_shares,
        "input_quantity_ids": [check[0] for check in provenance_checks],
        "missing_evidence": [],
    }


def _validate_allocation_provenance(
    quantity_repository: QuantityRepository,
    checks: list[tuple[str | None, str, float, str]],
) -> list[str]:
    """Require an existing, semantically matching ledger quantity for every input."""
    failures: list[str] = []
    for quantity_id, definition_key, expected_value, label in checks:
        if not quantity_id:
            failures.append(f"ledger provenance for {label}")
            continue
        quantity = quantity_repository.get(quantity_id)
        if quantity is None:
            failures.append(f"unknown ledger quantity {quantity_id} for {label}")
            continue
        if quantity.definition_key != definition_key:
            failures.append(f"unrelated ledger quantity {quantity_id} for {label}")
            continue
        if not isclose(quantity.value, float(expected_value), rel_tol=1e-12, abs_tol=0.0):
            failures.append(f"ledger quantity {quantity_id} does not match {label}")
    return failures


def _insufficient_allocation_result(allocator: str, missing_evidence: list[str]) -> dict[str, Any]:
    return {
        "status": "INSUFFICIENT_DATA",
        "allocator": allocator,
        "allocated_shares": {},
        "total_demand": None,
        "missing_evidence": missing_evidence,
    }


def _run_sensitivity_analysis_handler(
    payload: BaseModel,
    *,
    quantity_repository: QuantityRepository,
) -> dict[str, Any]:
    if not isinstance(payload, RunSensitivityAnalysisInput):
        raise TypeError("run_sensitivity_analysis received an unexpected input model.")
    projection_inputs = payload.scenario.get("projection_inputs")
    sensitivity_values = payload.inputs.get("sensitivity_parameter_values")
    baseline_ids = payload.inputs.get("baseline_quantity_ids")
    sensitivity_ids = payload.inputs.get("sensitivity_quantity_ids")
    missing = []
    if not isinstance(projection_inputs, dict):
        missing.append("explicit projection_inputs")
    if not isinstance(sensitivity_values, dict) or not sensitivity_values:
        missing.append("explicit sensitivity_parameter_values")
    if not isinstance(baseline_ids, dict):
        missing.append("ledger baseline_quantity_ids")
    if not isinstance(sensitivity_ids, dict):
        missing.append("ledger sensitivity_quantity_ids")
    if missing:
        return _insufficient_sensitivity_result(missing)

    try:
        expected_fields = set(FinancialScenario.__dataclass_fields__)
        if set(projection_inputs) != expected_fields:
            raise ValueError("projection_inputs must provide every FinancialScenario field exactly once")
        normalized_inputs = {
            name: tuple(values) if isinstance(values, list) else values
            for name, values in projection_inputs.items()
        }
        _baseline = FinancialScenario(**normalized_inputs)
        baseline_paths = _financial_numeric_paths(projection_inputs)
        if set(baseline_ids) != set(baseline_paths):
            raise ValueError("baseline_quantity_ids must map every projection input and no others")
        alternatives = _normalize_sensitivity_values(sensitivity_values, projection_inputs)
        if set(sensitivity_ids) != set(alternatives):
            raise ValueError("sensitivity_quantity_ids must map every sensitivity parameter and no others")

        evidence: list[tuple[str, str, float, str]] = []
        for path, value in baseline_paths.items():
            evidence.append((
                baseline_ids[path],
                f"finance.simulation.assumption.projection.{path}",
                value,
                f"projection assumption {path}",
            ))
        for path, values in alternatives.items():
            ids = sensitivity_ids[path]
            if not isinstance(ids, list) or len(ids) != len(values):
                raise ValueError(f"sensitivity_quantity_ids for {path} must match every alternative")
            for index, (quantity_id, value) in enumerate(zip(ids, values, strict=True), start=1):
                evidence.append((
                    quantity_id,
                    f"finance.simulation.assumption.sensitivity.{path}.{index}",
                    value,
                    f"sensitivity assumption {path} alternative {index}",
                ))
    except (TypeError, ValueError, KeyError) as exc:
        return _insufficient_sensitivity_result([str(exc)])

    invalid = _validate_sensitivity_provenance(quantity_repository, evidence)
    if invalid:
        return _insufficient_sensitivity_result(invalid)

    def evaluate(changed: Mapping[str, float]) -> Mapping[str, float]:
        values = dict(normalized_inputs)
        for path, value in changed.items():
            _set_financial_path(values, path, value)
        projection = project_monthly_cash_flow(FinancialScenario(
            **{name: tuple(value) if isinstance(value, list) else value for name, value in values.items()}
        ))
        return {
            "total_revenue": projection.total_revenue,
            "total_debt_service": projection.total_debt_service,
            "minimum_cash": projection.minimum_cash,
        }

    try:
        baseline_parameters = {path: _financial_path_value(projection_inputs, path) for path in alternatives}
        result = run_one_at_a_time_sensitivity(
            evaluate,
            baseline_parameters=baseline_parameters,
            parameter_values=alternatives,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        return _insufficient_sensitivity_result([f"valid sensitivity calculation inputs: {exc}"])

    points = []
    occurrence: dict[str, int] = {}
    for point in result.points:
        index = occurrence.get(point.parameter, 0)
        quantity_id = sensitivity_ids[point.parameter][index]
        occurrence[point.parameter] = index + 1
        points.append({
            "parameter": point.parameter,
            "value": point.value,
            "quantity_id": quantity_id,
            "outputs": dict(point.outputs),
            "deltas": dict(point.deltas),
        })
    return {
        "status": "COMPLETED",
        "baseline_outputs": dict(result.baseline_outputs),
        "points": points,
        "input_quantity_ids": [item[0] for item in evidence],
        "missing_evidence": [],
    }


def _insufficient_sensitivity_result(missing_evidence: list[str]) -> dict[str, Any]:
    return {
        "status": "INSUFFICIENT_DATA",
        "baseline_outputs": {},
        "points": [],
        "input_quantity_ids": [],
        "missing_evidence": missing_evidence,
    }


def _financial_numeric_paths(values: Mapping[str, Any]) -> dict[str, float]:
    output: dict[str, float] = {}
    for name, value in values.items():
        if isinstance(value, list):
            for index, item in enumerate(value, start=1):
                output[f"{name}.{index}"] = float(item)
        else:
            output[name] = float(value)
    if not all(isfinite(value) for value in output.values()):
        raise ValueError("projection inputs must contain only finite numeric values")
    return output


def _normalize_sensitivity_values(
    alternatives: Mapping[str, Any], projection_inputs: Mapping[str, Any]
) -> dict[str, tuple[float, ...]]:
    normalized: dict[str, tuple[float, ...]] = {}
    for path, values in alternatives.items():
        _financial_path_value(projection_inputs, path)
        if not isinstance(values, list) or not values:
            raise ValueError(f"sensitivity alternatives for {path} must be a non-empty list")
        numbers = tuple(float(value) for value in values)
        if not all(isfinite(value) for value in numbers):
            raise ValueError(f"sensitivity alternatives for {path} must be finite")
        normalized[path] = numbers
    return normalized


def _financial_path_value(values: Mapping[str, Any], path: str) -> float:
    parts = path.split(".")
    if len(parts) == 1 and parts[0] in values and not isinstance(values[parts[0]], list):
        return float(values[parts[0]])
    if len(parts) == 2 and parts[0] in values and parts[1].isdigit():
        items = values[parts[0]]
        index = int(parts[1]) - 1
        if isinstance(items, list) and 0 <= index < len(items):
            return float(items[index])
    raise ValueError(f"unknown financial sensitivity parameter {path!r}")


def _set_financial_path(values: dict[str, Any], path: str, value: float) -> None:
    parts = path.split(".")
    if len(parts) == 1 and parts[0] in values and not isinstance(values[parts[0]], list):
        values[parts[0]] = value
        return
    if len(parts) == 2 and parts[0] in values and parts[1].isdigit():
        index = int(parts[1]) - 1
        if isinstance(values[parts[0]], list) and 0 <= index < len(values[parts[0]]):
            values[parts[0]][index] = value
            return
    raise ValueError(f"unknown financial sensitivity parameter {path!r}")


def _validate_sensitivity_provenance(
    repository: QuantityRepository,
    checks: list[tuple[str, str, float, str]],
) -> list[str]:
    failures: list[str] = []
    for quantity_id, definition_key, expected_value, label in checks:
        if not isinstance(quantity_id, str) or not quantity_id.strip():
            failures.append(f"ledger quantity ID for {label}")
            continue
        quantity = repository.get(quantity_id)
        if quantity is None:
            failures.append(f"unknown ledger quantity {quantity_id} for {label}")
        elif (
            quantity.definition_key != definition_key
            or quantity.kind not in {Kind.USER_ASSUMED, Kind.SCENARIO}
            or not isclose(quantity.value, expected_value, rel_tol=1e-12, abs_tol=0.0)
        ):
            failures.append(f"ledger quantity {quantity_id} does not match {label}")
    return failures


def _create_followup_tasks_handler(payload: BaseModel) -> dict[str, Any]:
    if not isinstance(payload, CreateFollowupTasksInput):
        raise TypeError("create_followup_tasks received an unexpected input model.")
    tasks = tasks_from_unresolved_gaps(payload.unresolved_gaps)
    return {
        "task_count": len(tasks),
        "tasks": tasks,
    }


def _fetch_economic_indicator_handler(
    payload: BaseModel,
    *,
    quantity_repository: QuantityRepository,
) -> dict[str, Any]:
    if not isinstance(payload, FetchEconomicIndicatorInput):
        raise TypeError("fetch_economic_indicator received an unexpected input model.")
    quantities = []
    if hasattr(quantity_repository, "list_by_definition"):
        quantities = quantity_repository.list_by_definition(payload.series)
    elif hasattr(quantity_repository, "list_all"):
        quantities = [q for q in quantity_repository.list_all() if q.definition_key == payload.series]

    matches = [q for q in quantities if q.geo_unit_id == payload.geo_id]
    if payload.source and payload.source != "*":
        filtered = []
        for q in matches:
            for s_id, _, _ in q.source_refs:
                if s_id.lower() == payload.source.lower() or payload.source.lower() in s_id.lower():
                    filtered.append(q)
                    break
        matches = filtered

    if not matches:
        return {
            "status": "INSUFFICIENT_DATA",
            "source": payload.source,
            "geo_id": payload.geo_id,
            "series": payload.series,
            "quantities": [],
            "missing_evidence": [
                f"indicator '{payload.series}' for '{payload.geo_id}' from source '{payload.source}'"
            ],
        }

    return {
        "status": "COMPLETED",
        "source": payload.source,
        "geo_id": payload.geo_id,
        "series": payload.series,
        "quantities": [
            {
                "id": str(q.id),
                "definition_key": q.definition_key,
                "value": q.value,
                "unit": q.unit,
                "kind": q.kind.value if hasattr(q.kind, "value") else str(q.kind),
                "evidence_floor": q.evidence_floor,
                "as_of": str(q.as_of),
            }
            for q in matches
        ],
        "missing_evidence": [],
    }


def _search_policy_documents_handler(
    payload: BaseModel,
    *,
    policy_repository: PolicyRuleRepository,
) -> dict[str, Any]:
    if not isinstance(payload, SearchPolicyDocumentsInput):
        raise TypeError("search_policy_documents received an unexpected input model.")
    rules = policy_repository.list_rules_by_scheme(payload.scheme)
    passages = []
    q_lower = payload.query.lower().strip()
    for rule in rules:
        rule_key = str(rule.get("rule_key") or "")
        citations = rule.get("source_references") or []
        note = str(rule.get("approval_note") or "")
        matches_query = (
            not q_lower
            or q_lower in rule_key.lower()
            or q_lower in note.lower()
            or any(
                q_lower in str(c.get("locator", "")).lower()
                or q_lower in str(c.get("document_url", "")).lower()
                for c in citations
            )
        )
        if matches_query:
            for citation in citations:
                passages.append({
                    "rule_key": rule_key,
                    "scheme_id": payload.scheme,
                    "document_id": str(citation.get("document_id", "")),
                    "locator": citation.get("locator", ""),
                    "source_version_id": citation.get("source_version_id", ""),
                    "document_url": citation.get("document_url", ""),
                })
    if not passages:
        return {
            "status": "INSUFFICIENT_DATA",
            "scheme": payload.scheme,
            "query": payload.query,
            "passages": [],
            "missing_evidence": [
                f"policy passages for scheme '{payload.scheme}' matching '{payload.query}'"
            ],
        }
    return {
        "status": "COMPLETED",
        "scheme": payload.scheme,
        "query": payload.query,
        "passages": passages,
        "missing_evidence": [],
    }


def _verify_claim_handler(
    payload: BaseModel,
    *,
    quantity_repository: QuantityRepository,
) -> dict[str, Any]:
    if not isinstance(payload, VerifyClaimInput):
        raise TypeError("verify_claim received an unexpected input model.")
    claim_text = payload.claim.strip()
    matched = None
    if quantity_repository.exists(claim_text):
        matched = quantity_repository.get(claim_text)
    elif hasattr(quantity_repository, "list_all"):
        for q in quantity_repository.list_all():
            if q.definition_key in claim_text or str(q.id) in claim_text:
                matched = q
                break

    if matched is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "claim": claim_text,
            "verdict": "UNVERIFIED",
            "evidence": [],
            "missing_evidence": [f"authoritative evidence for claim: {claim_text}"],
        }

    return {
        "status": "COMPLETED",
        "claim": claim_text,
        "verdict": "VERIFIED",
        "evidence": [
            {
                "quantity_id": str(matched.id),
                "definition_key": matched.definition_key,
                "value": matched.value,
                "evidence_floor": matched.evidence_floor,
                "as_of": str(matched.as_of),
            }
        ],
        "missing_evidence": [],
    }


def _evaluate_scheme_eligibility_handler(
    payload: BaseModel,
    *,
    policy_repository: PolicyRuleRepository,
) -> dict[str, Any]:
    if not isinstance(payload, EvaluateSchemeEligibilityInput):
        raise TypeError("evaluate_scheme_eligibility received an unexpected input model.")
    rules = policy_repository.list_rules_by_scheme(payload.scheme)
    if not rules:
        from backend.arthlens.policy.scheme_rules import SCHEME_REGISTRY, get_scheme_rule_set

        candidate = get_scheme_rule_set(payload.scheme)
        if not candidate:
            for s_id, s_obj in SCHEME_REGISTRY.items():
                if payload.scheme.lower() in s_id.lower() or payload.scheme.lower() in s_obj.official_name.lower():
                    candidate = s_obj
                    break

        if candidate and not candidate.is_approved_for_advice:
            trace = candidate.evaluate_eligibility_trace(payload.facts)
            return {
                "status": "UNAPPROVED_CANDIDATE_RULE",
                "scheme": candidate.official_name,
                "eligibility": "UNKNOWN",
                "results": [
                    {
                        "rule_key": candidate.scheme_id,
                        "result": trace.result.value,
                        "reason": f"Candidate extraction: {trace.reason} (Formal human approval pending)",
                    }
                ],
                "missing_evidence": [
                    f"Official human approval for {candidate.official_name} rules (P0-2/Gate 2)"
                ],
                "disclaimer": "Rule extraction is candidate research only (HUMAN_REVIEW_REQUIRED). Not legal or financial advice.",
            }

        return {
            "status": "INSUFFICIENT_DATA",
            "scheme": payload.scheme,
            "eligibility": "UNKNOWN",
            "results": [],
            "missing_evidence": [f"policy rules for scheme '{payload.scheme}'"],
        }

    evaluator = EligibilityEvaluator(payload.facts)
    results = []
    overall_eligible = True
    unknown_facts = set()

    for rule in rules:
        ast_data = rule.get("rule_ast")
        if not ast_data:
            continue
        try:
            node = parse_rule_ast(ast_data)
            trace = evaluator.evaluate(node)
            status_str = trace.result.value
            results.append({
                "rule_key": rule.get("rule_key"),
                "result": status_str,
                "reason": trace.reason,
            })
            if trace.result == TruthValue.UNKNOWN:
                overall_eligible = False
                if trace.fact:
                    unknown_facts.add(trace.fact)
            elif trace.result == TruthValue.FALSE:
                overall_eligible = False
        except Exception as exc:
            results.append({
                "rule_key": rule.get("rule_key"),
                "result": "UNKNOWN",
                "reason": str(exc),
            })
            overall_eligible = False

    if unknown_facts:
        return {
            "status": "INSUFFICIENT_DATA",
            "scheme": payload.scheme,
            "eligibility": "UNKNOWN",
            "results": results,
            "missing_evidence": [f"fact {fact}" for fact in sorted(unknown_facts)],
        }

    return {
        "status": "COMPLETED",
        "scheme": payload.scheme,
        "eligibility": "ELIGIBLE" if overall_eligible else "INELIGIBLE",
        "results": results,
        "missing_evidence": [],
    }


def _compute_catchment_handler(
    payload: BaseModel,
    *,
    road_graph_repository: PostgresRoadGraphRepository | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, ComputeCatchmentInput):
        raise TypeError("compute_catchment received an unexpected input model.")
    site_dict = payload.site
    lon = site_dict.get("longitude") or site_dict.get("lon")
    lat = site_dict.get("latitude") or site_dict.get("lat")
    if lon is None or lat is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "minutes": payload.minutes,
            "missing_evidence": ["site coordinates (longitude and latitude)"],
        }
    graph = site_dict.get("graph")
    source_version_id = site_dict.get("source_version_id")
    repo = road_graph_repository or PostgresRoadGraphRepository()
    try:
        if graph is None and source_version_id:
            graph = repo.extract_local_subgraph(
                source_version_id=str(source_version_id),
                site=(float(lon), float(lat)),
            )
        if graph is None:
            return {
                "status": "INSUFFICIENT_DATA",
                "minutes": payload.minutes,
                "missing_evidence": ["active registered road graph"],
            }
        speeds_dict = site_dict.get(
            "speeds",
            {
                "motorway": 60.0,
                "trunk": 50.0,
                "primary": 40.0,
                "secondary": 30.0,
                "tertiary": 25.0,
                "residential": 20.0,
                "unclassified": 20.0,
                "service": 15.0,
            },
        )
        speed_scenario = RoadSpeedScenario("scenario-speed", speeds_dict)
        corridor_width = float(site_dict.get("corridor_width_m", 500.0))
        analysis = build_catchments(
            graph,
            site=(float(lon), float(lat)),
            speeds=speed_scenario,
            thresholds_minutes=(float(payload.minutes),),
            corridor_width_m=corridor_width,
        )
        catchment = analysis.catchments[0]
        return {
            "status": "COMPLETED",
            "minutes": payload.minutes,
            "mode": payload.mode,
            "nodes_reached": len(catchment.reachable_node_ids),
            "reachable_nodes": list(catchment.reachable_node_ids),
            "geometry": catchment.geometry,
            "missing_evidence": [],
        }
    except Exception as exc:
        return {
            "status": "INSUFFICIENT_DATA",
            "minutes": payload.minutes,
            "missing_evidence": [str(exc)],
        }


def _run_business_scenario_handler(payload: BaseModel) -> dict[str, Any]:
    if not isinstance(payload, RunBusinessScenarioInput):
        raise TypeError("run_business_scenario received an unexpected input model.")
    scenario_dict = payload.scenario.get("projection_inputs") or payload.scenario
    try:
        expected_fields = set(FinancialScenario.__dataclass_fields__)
        missing = sorted(expected_fields - set(scenario_dict))
        if missing:
            return {
                "status": "INSUFFICIENT_DATA",
                "total_revenue": None,
                "missing_evidence": [f"financial scenario field: {f}" for f in missing],
            }
        normalized = {
            name: tuple(values) if isinstance(values, list) else values
            for name, values in scenario_dict.items()
            if name in expected_fields
        }
        scenario = FinancialScenario(**normalized)
        projection = project_monthly_cash_flow(scenario)
        total_opex = sum(m.operating_expenses for m in projection.months)
        return {
            "status": "COMPLETED",
            "total_revenue": projection.total_revenue,
            "total_operating_expenses": total_opex,
            "total_debt_service": projection.total_debt_service,
            "minimum_cash": projection.minimum_cash,
            "ending_cash": (
                projection.months[-1].closing_cash
                if projection.months
                else 0.0
            ),
            "months": len(projection.months),
            "monthly_summary": [
                {
                    "month": m.month,
                    "revenue": m.revenue,
                    "net_cash_flow": m.cash_flow,
                    "closing_cash": m.closing_cash,
                    "dscr": m.dscr,
                }
                for m in projection.months
            ],
            "missing_evidence": [],
        }
    except Exception as exc:
        return {
            "status": "INSUFFICIENT_DATA",
            "total_revenue": None,
            "missing_evidence": [f"financial projection input error: {exc}"],
        }


def _compare_scenarios_handler(
    payload: BaseModel,
    *,
    scenario_repository: ScenarioRepository | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, CompareScenariosInput):
        raise TypeError("compare_scenarios received an unexpected input model.")
    repo = scenario_repository or PostgresScenarioRepository()
    scenarios = []
    missing_ids = []
    for run_id in payload.run_ids:
        sc = repo.get_scenario(run_id) if hasattr(repo, "get_scenario") else None
        if sc is None and hasattr(repo, "get_simulation_run"):
            sc = repo.get_simulation_run(run_id)
        if sc is None:
            missing_ids.append(run_id)
        else:
            scenarios.append(sc)
    if missing_ids:
        return {
            "status": "INSUFFICIENT_DATA",
            "compared_count": 0,
            "scenarios": [],
            "missing_evidence": [f"scenario/run record '{rid}'" for rid in missing_ids],
        }
    comparison_matrix = {}
    for sc in scenarios:
        s_id = str(sc.get("id"))
        comparison_matrix[s_id] = {
            "name": sc.get("name", s_id),
            "status": sc.get("status", "ACTIVE"),
            "break_even_units": sc.get("break_even_units"),
            "monthly_emi": sc.get("monthly_emi"),
            "total_interest": sc.get("total_interest"),
            "captured_market_demand": sc.get("captured_market_demand"),
            "market_share_fraction": sc.get("market_share_fraction"),
            "viability_status": sc.get("viability_status"),
        }
    return {
        "status": "COMPLETED",
        "compared_count": len(scenarios),
        "scenarios": scenarios,
        "comparison_matrix": comparison_matrix,
        "summary": f"Successfully compared {len(scenarios)} scenarios.",
        "missing_evidence": [],
    }


def _generate_report_handler(payload: BaseModel) -> dict[str, Any]:
    if not isinstance(payload, GenerateReportInput):
        raise TypeError("generate_report received an unexpected input model.")
    graph = payload.verified_claim_graph
    if not graph or not isinstance(graph, dict):
        return {
            "status": "INSUFFICIENT_DATA",
            "missing_evidence": ["verified claim graph"],
        }
    claims = graph.get("claims") or graph.get("nodes") or []
    if not claims and "title" not in graph and "summary" not in graph:
        return {
            "status": "INSUFFICIENT_DATA",
            "missing_evidence": ["claims or summary in verified claim graph"],
        }
    report_id = str(uuid.uuid4())
    return {
        "status": "COMPLETED",
        "report_id": report_id,
        "title": graph.get("title", "ArthLens Analytical Dossier"),
        "verified_claims_count": len(claims),
        "summary": graph.get("summary", "Analytical dossier verified from authoritative quantities."),
        "claims": claims,
        "methodology": graph.get("methodology", "Deterministic multi-tier verification"),
        "missing_evidence": [],
    }


def _publish_to_shared_view_handler(
    payload: BaseModel,
    *,
    agent_run_repository: PostgresAgentRunRepository | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, PublishToSharedViewInput):
        raise TypeError("publish_to_shared_view received an unexpected input model.")
    repo = agent_run_repository or PostgresAgentRunRepository()
    run = repo.get_run(payload.run_id) if hasattr(repo, "get_run") else None
    if run is None and not (hasattr(repo, "exists") and repo.exists(payload.run_id)):
        return {
            "status": "INSUFFICIENT_DATA",
            "missing_evidence": [f"agent run '{payload.run_id}'"],
        }
    share_token = str(uuid.uuid4())
    return {
        "status": "COMPLETED",
        "run_id": payload.run_id,
        "share_token": share_token,
        "shared_view_url": f"/shared/view/{payload.run_id}?token={share_token}",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "missing_evidence": [],
    }


def build_production_tool_executor(
    quantity_repository: QuantityRepository | None = None,
    policy_repository: PolicyRuleRepository | None = None,
    road_graph_repository: PostgresRoadGraphRepository | None = None,
    scenario_repository: ScenarioRepository | None = None,
    agent_run_repository: PostgresAgentRunRepository | None = None,
    approval_check: ApprovalCheck | None = None,
) -> ToolExecutionRegistry:
    """Build tool executor with all 14 deterministic computational handlers."""
    schemas = build_default_tool_registry()
    quantity_repo = quantity_repository or PostgresQuantityRepository()
    policy_repo = policy_repository or PostgresPolicyRuleRepository()
    road_repo = road_graph_repository or PostgresRoadGraphRepository()
    scenario_repo = scenario_repository or PostgresScenarioRepository()
    run_repo = agent_run_repository or PostgresAgentRunRepository()

    handlers = {
        "calculate_break_even": _calculate_break_even,
        "calculate_loan_schedule": _calculate_loan_schedule,
        "allocate_spatial_demand": partial(
            _allocate_spatial_demand_handler,
            quantity_repository=quantity_repo,
        ),
        "run_sensitivity_analysis": partial(
            _run_sensitivity_analysis_handler,
            quantity_repository=quantity_repo,
        ),
        "create_followup_tasks": _create_followup_tasks_handler,
        "fetch_economic_indicator": partial(
            _fetch_economic_indicator_handler,
            quantity_repository=quantity_repo,
        ),
        "search_policy_documents": partial(
            _search_policy_documents_handler,
            policy_repository=policy_repo,
        ),
        "verify_claim": partial(
            _verify_claim_handler,
            quantity_repository=quantity_repo,
        ),
        "evaluate_scheme_eligibility": partial(
            _evaluate_scheme_eligibility_handler,
            policy_repository=policy_repo,
        ),
        "compute_catchment": partial(
            _compute_catchment_handler,
            road_graph_repository=road_repo,
        ),
        "run_business_scenario": _run_business_scenario_handler,
        "compare_scenarios": partial(
            _compare_scenarios_handler,
            scenario_repository=scenario_repo,
        ),
        "generate_report": _generate_report_handler,
        "publish_to_shared_view": partial(
            _publish_to_shared_view_handler,
            agent_run_repository=run_repo,
        ),
    }
    return ToolExecutionRegistry(schemas, handlers, approval_check=approval_check)


def default_production_verifier(
    objective: Mapping[str, Any],
    outputs: tuple[dict[str, Any], ...],
) -> bool:
    """Verify the registered deterministic result and reject incomplete evidence."""
    if not isinstance(objective, Mapping) or not isinstance(outputs, tuple) or not outputs:
        return False
    schemas = build_default_tool_registry()
    for item in outputs:
        if not isinstance(item, dict) or not isinstance(item.get("tool_name"), str):
            return False
        tool_name = item["tool_name"]
        tool_input = item.get("tool_input")
        result = item.get("result")
        if not isinstance(tool_input, dict) or not isinstance(result, dict):
            return False
        if result.get("status") == "INSUFFICIENT_DATA":
            return False
        try:
            if tool_name == "calculate_break_even":
                expected = _calculate_break_even(schemas.validate_input(tool_name, tool_input))
                if result != expected:
                    return False
            elif tool_name == "calculate_loan_schedule":
                expected = _calculate_loan_schedule(schemas.validate_input(tool_name, tool_input))
                if result != expected:
                    return False
            elif tool_name == "allocate_spatial_demand":
                if (
                    result.get("status") != "COMPLETED"
                    or not result.get("input_quantity_ids")
                    or result.get("missing_evidence") != []
                    or not isinstance(result.get("allocated_shares"), dict)
                    or not _finite_tree(result)
                ):
                    return False
            elif tool_name == "run_sensitivity_analysis":
                if (
                    result.get("status") != "COMPLETED"
                    or not result.get("input_quantity_ids")
                    or not isinstance(result.get("baseline_outputs"), dict)
                    or not result.get("baseline_outputs")
                    or not isinstance(result.get("points"), list)
                    or not result.get("points")
                    or result.get("missing_evidence") != []
                    or not _finite_tree(result)
                ):
                    return False
            elif tool_name == "create_followup_tasks":
                if (
                    not isinstance(result.get("tasks"), list)
                    or result.get("task_count") != len(result["tasks"])
                    or result.get("task_count", 0) <= 0
                ):
                    return False
            elif tool_name == "fetch_economic_indicator":
                if (
                    result.get("status") != "COMPLETED"
                    or not isinstance(result.get("quantities"), list)
                    or len(result["quantities"]) == 0
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "search_policy_documents":
                if (
                    result.get("status") != "COMPLETED"
                    or not isinstance(result.get("passages"), list)
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "verify_claim":
                if (
                    result.get("status") != "COMPLETED"
                    or result.get("verdict") != "VERIFIED"
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "evaluate_scheme_eligibility":
                if (
                    result.get("status") != "COMPLETED"
                    or result.get("eligibility") not in ("ELIGIBLE", "INELIGIBLE")
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "compute_catchment":
                if (
                    result.get("status") != "COMPLETED"
                    or result.get("nodes_reached", 0) <= 0
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "run_business_scenario":
                if (
                    result.get("status") != "COMPLETED"
                    or result.get("total_revenue") is None
                    or not _finite_tree(result)
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "compare_scenarios":
                if (
                    result.get("status") != "COMPLETED"
                    or result.get("compared_count", 0) <= 0
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "generate_report":
                if (
                    result.get("status") != "COMPLETED"
                    or not result.get("report_id")
                    or result.get("missing_evidence") != []
                ):
                    return False
            elif tool_name == "publish_to_shared_view":
                if (
                    result.get("status") != "COMPLETED"
                    or not result.get("share_token")
                    or result.get("missing_evidence") != []
                ):
                    return False
            else:
                return False
        except (KeyError, TypeError, ValueError):
            return False
    return True


def run_worker_loop(
    poll_interval: float = 1.0,
    stop_event: Any | None = None,
    max_iterations: int | None = None,
    orchestrator: AgentRunOrchestrator | None = None,
    repository: PostgresAgentRunRepository | None = None,
    worker_id: str | None = None,
    lease_duration_seconds: int = 300,
) -> int:
    """
    Independent durable worker loop that claims pending runs with
    PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED, executes them through
    the deterministic orchestrator, and recovers stale/crashed runs.
    """
    repo = repository or PostgresAgentRunRepository()
    orch = orchestrator or create_default_orchestrator(repository=repo)
    worker_token = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
    processed = 0
    iterations = 0

    logger.info(
        "Durable agent worker loop started (worker_id=%s, poll_interval=%.2fs)",
        worker_token,
        poll_interval,
    )

    while True:
        if stop_event is not None and stop_event.is_set():
            logger.info("Worker loop received stop signal.")
            break
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        try:
            # First, recover any stale runs
            recovered = repo.recover_stale_runs(timeout_seconds=lease_duration_seconds)
            if recovered > 0:
                logger.warning("Recovered %d stale runs.", recovered)

            # Claim next available pending run
            try:
                claimed = repo.claim_pending_run(
                    worker_id=worker_token,
                    lease_duration_seconds=lease_duration_seconds,
                )
            except TypeError:
                claimed = repo.claim_pending_run()

            if claimed:
                run_id = claimed["id"]
                logger.info("Claimed pending agent run: %s (state: %s)", run_id, claimed.get("state"))
                try:
                    if claimed.get("state") == AgentRunState.RECOVERING.value and hasattr(orch, "resume"):
                        res = orch.resume(run_id)
                    else:
                        res = orch.run(run_id)
                    processed += 1
                    logger.info("Run %s completed with state: %s", run_id, res.state.value)
                finally:
                    if hasattr(repo, "release_claim"):
                        try:
                            repo.release_claim(run_id, worker_id=worker_token)
                        except TypeError:
                            repo.release_claim(run_id)
            else:
                if stop_event is not None:
                    stop_event.wait(poll_interval)
                else:
                    time.sleep(poll_interval)
        except Exception as exc:
            logger.exception("Error in worker loop: %s", exc)
            time.sleep(poll_interval)

    return processed


def _finite_tree(value: Any) -> bool:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return isfinite(float(value))
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_tree(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(_finite_tree(item) for item in value)
    return False


def create_default_orchestrator(
    repository: Any | None = None,
    llm_client: Any | None = None,
    task_repository: Any | None = None,
) -> AgentRunOrchestrator:
    """Instantiate a production-ready agent orchestrator."""
    repo = repository or PostgresAgentRunRepository()
    task_repo = task_repository or PostgresFollowupTaskRepository()
    client = llm_client or get_llm_client()
    tools = build_default_tool_registry()
    validator = PlanValidator(tools, max_steps=25)
    interpreter = GoalInterpreter(client)
    planner = Planner(client, validator, budget_limits=RunBudgetLimits())
    executor = build_production_tool_executor()

    def model_cost_calc(task_type: str) -> Decimal:
        return Decimal("0.001")

    return AgentRunOrchestrator(
        repository=repo,
        goal_interpreter=interpreter,
        planner=planner,
        executor=executor,
        model_call_cost=model_cost_calc,
        verifier=default_production_verifier,
        task_repository=task_repo,
    )


def execute_agent_run_background(
    run_id: str,
    worker_id: str | None = None,
    repository: PostgresAgentRunRepository | None = None,
    orchestrator: AgentRunOrchestrator | None = None,
) -> OrchestrationResult:
    """
    Entrypoint invoked by FastAPI background tasks or dedicated workers to execute
    an agent run from CREATED through to terminal state.
    """
    repo = repository or PostgresAgentRunRepository()
    worker_token = worker_id or f"bg-worker-{uuid.uuid4().hex[:8]}"
    logger.info("Starting background execution for agent run: %s (worker: %s)", run_id, worker_token)
    if hasattr(repo, "claim_run_by_id"):
        claimed = repo.claim_run_by_id(run_id, worker_id=worker_token)
        if not claimed:
            logger.warning(
                "Could not claim run %s; already claimed by another worker or in terminal state.",
                run_id,
            )
            run = repo.get_run(run_id)
            if run is None:
                raise KeyError(f"Agent run {run_id} was not found.")
            return OrchestrationResult(
                run_id=run_id,
                state=AgentRunState(run["state"]),
                outputs=(),
                missing_slots=(),
                reason="already_claimed_or_completed",
            )

    orch = orchestrator or create_default_orchestrator(repository=repo)
    try:
        run = repo.get_run(run_id)
        if run and run.get("state") == AgentRunState.RECOVERING.value and hasattr(orch, "resume"):
            result = orch.resume(run_id)
        else:
            result = orch.run(run_id)
        logger.info(
            "Agent run %s completed with state %s (reason: %s)",
            run_id,
            result.state.value,
            result.reason,
        )
        return result
    except Exception as exc:
        logger.exception("Agent run %s failed unexpectedly: %s", run_id, exc)
        raise
    finally:
        if hasattr(repo, "release_claim"):
            try:
                repo.release_claim(run_id, worker_id=worker_token)
            except TypeError:
                repo.release_claim(run_id)


__all__ = [
    "build_production_tool_executor",
    "create_default_orchestrator",
    "default_production_verifier",
    "execute_agent_run_background",
    "run_worker_loop",
]
