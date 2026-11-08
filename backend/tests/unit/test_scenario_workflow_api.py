from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

from backend.arthlens.api import scenarios as scenarios_api
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.geo.road_graph import RoadEdge, RoadGraph, RoadNode

OWNER = "owner-1"
SCENARIO_ID = "scenario-1"
GEO_ID = "in:district:120"
TODAY = date.today().isoformat()


def _quantity(definition: str, value: float, unit: str, *, owner: str = OWNER, geo: str = GEO_ID) -> Quantity:
    return Quantity(
        id=str(uuid.uuid4()),
        definition_key=definition,
        value=value,
        unit=unit,
        kind=Kind.USER_ASSUMED,
        evidence_floor=3,
        geo_unit_id=geo,
        resolution=2,
        as_of=TODAY,
        source_refs=((f"user:{owner}", "scenario:scenario-1/input", TODAY),),
        method_id="explicit_user_input",
        model_version="1",
        owner_id=owner,
    )


class _ScenarioRepo:
    def __init__(self, scenarios=None):
        self.scenarios = scenarios or {
            SCENARIO_ID: {
                "id": SCENARIO_ID,
                "owner_id": OWNER,
                "name": "Test enterprise",
                "scenario": {"geo_id": GEO_ID},
            }
        }
        self.comparisons = {}

    def get_scenario_by_id_and_owner(self, scenario_id, owner_id):
        record = self.scenarios.get(str(scenario_id))
        if record and record["owner_id"] == owner_id:
            return record
        return None

    def save_scenario(self, record):
        self.scenarios[record["id"]] = record
        return record["id"]

    def save_comparison(self, record):
        comparison_id = str(uuid.uuid4())
        self.comparisons[comparison_id] = {**record, "id": comparison_id}
        return comparison_id

    def get_comparison_by_id_and_owner(self, comparison_id, owner_id):
        record = self.comparisons.get(str(comparison_id))
        return record if record and record["owner_id"] == owner_id else None


class _GeoRepo:
    def get_by_id(self, geo_id):
        if geo_id == GEO_ID:
            return SimpleNamespace(
                id=GEO_ID,
                parent_id="in:state:09",
                level=2,
                geometry_status="GEOMETRY_VERIFIED",
                geometry_source_record_id="boundary-record-120",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[
                        [80.8, 25.3], [81.0, 25.3], [81.0, 25.5],
                        [80.8, 25.5], [80.8, 25.3],
                    ]],
                },
            )
        if geo_id == "in:state:09":
            return SimpleNamespace(id=geo_id, parent_id="in", level=1)
        if geo_id == "in":
            return SimpleNamespace(id=geo_id, parent_id=None, level=0)
        return None


class _SourceRepo:
    def get_version(self, version_id):
        return None

    def get_source(self, source_id):
        return None


class _ActiveRoadSourceRepo(_SourceRepo):
    def get_version(self, version_id):
        if version_id == "road-version-1":
            return {"id": version_id, "source_id": "DS-04", "status": "ACTIVE"}
        if version_id == "boundary-version-120":
            return {"id": version_id, "source_id": "DS-09", "status": "ACTIVE"}
        return None

    def get_source(self, source_id):
        return {"id": source_id, "status": "ACTIVE"} if source_id in {"DS-04", "DS-09"} else None


class _GeometrySourceRecordRepo:
    def get_by_id(self, record_id):
        if record_id == "boundary-record-120":
            return SimpleNamespace(
                source_version_id="boundary-version-120",
                source_id="DS-09",
                geo_unit_id=GEO_ID,
            )
        return None


class _QuantityRepo:
    def __init__(self, quantities=()):
        self.quantities = {quantity.id: quantity for quantity in quantities}

    def get(self, quantity_id):
        return self.quantities.get(str(quantity_id))

    def save_many(self, quantities, session=None):
        self.quantities.update({quantity.id: quantity for quantity in quantities})


def _spatial_payload(quantity_ids):
    return scenarios_api.SpatialScenarioRequest.model_validate({
        "allocator_type": "nearest",
        "candidate_facility_id": "candidate",
        "zones": [{"zone_id": GEO_ID, "quantity_id": quantity_ids["demand"]}],
        "facilities": [{"facility_id": "candidate", "quantity_id": quantity_ids["facility"]}],
        "travel_time_quantity_ids": {GEO_ID: {"candidate": quantity_ids["travel"]}},
    })


def test_spatial_scenario_uses_registered_role_matched_quantities_and_persists_outputs(monkeypatch):
    demand = _quantity("demand.zone.monthly", 1200, "INR/month")
    facility = _quantity("facility.attractiveness", 1.5, "dimensionless")
    travel = _quantity("travel_time.minutes", 12, "minute")
    quantities = _QuantityRepo([demand, facility, travel])
    scenarios = _ScenarioRepo()
    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", lambda: scenarios)
    monkeypatch.setattr(scenarios_api, "PostgresGeoUnitRepository", _GeoRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRepository", _SourceRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRecordRepository", _GeometrySourceRecordRepo)
    monkeypatch.setattr(scenarios_api, "PostgresQuantityRepository", lambda: quantities)

    result = scenarios_api.allocate_scenario_spatial_demand(
        SCENARIO_ID,
        _spatial_payload({"demand": demand.id, "facility": facility.id, "travel": travel.id}),
        SimpleNamespace(id=OWNER),
    )

    assert result["status"] == "COMPLETED"
    assert result["captured_demand_inr_monthly"] == 1200
    assert result["market_share_fraction"] == 1
    assert result["input_quantity_ids"][f"zone_demand:{GEO_ID}"] == demand.id
    demand_output = quantities.get(result["quantity_ids"]["captured_demand"])
    share_output = quantities.get(result["quantity_ids"]["market_share"])
    assert demand_output is not None and demand_output.parent_ids == (demand.id, facility.id, travel.id)
    assert share_output is not None and share_output.parent_ids == (demand_output.id,)
    assert scenarios.scenarios[SCENARIO_ID]["scenario"]["spatial_demand"]["execution_id"] == result["execution_id"]


def test_spatial_scenario_returns_insufficient_data_for_unknown_quantity_ids(monkeypatch):
    scenarios = _ScenarioRepo()
    quantities = _QuantityRepo()
    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", lambda: scenarios)
    monkeypatch.setattr(scenarios_api, "PostgresGeoUnitRepository", _GeoRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRepository", _SourceRepo)
    monkeypatch.setattr(scenarios_api, "PostgresQuantityRepository", lambda: quantities)
    unknown = str(uuid.uuid4())

    result = scenarios_api.allocate_scenario_spatial_demand(
        SCENARIO_ID,
        _spatial_payload({"demand": unknown, "facility": str(uuid.uuid4()), "travel": str(uuid.uuid4())}),
        SimpleNamespace(id=OWNER),
    )

    assert result["status"] == "INSUFFICIENT_DATA"
    assert any("not registered" in issue for issue in result["missing_evidence"])
    assert result["quantity_ids"] == {}


def test_spatial_scenario_huff_uses_explicit_decay_quantity(monkeypatch):
    demand = _quantity("demand.zone.monthly", 100, "INR/month")
    candidate = _quantity("facility.attractiveness", 2, "dimensionless")
    competitor = _quantity("facility.attractiveness", 1, "dimensionless")
    candidate_time = _quantity("travel_time.minutes", 5, "minute")
    competitor_time = _quantity("travel_time.minutes", 10, "minute")
    decay = _quantity("demand.huff.lambda", 1, "dimensionless")
    quantities = _QuantityRepo([demand, candidate, competitor, candidate_time, competitor_time, decay])
    scenarios = _ScenarioRepo()
    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", lambda: scenarios)
    monkeypatch.setattr(scenarios_api, "PostgresGeoUnitRepository", _GeoRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRepository", _SourceRepo)
    monkeypatch.setattr(scenarios_api, "PostgresQuantityRepository", lambda: quantities)
    request = scenarios_api.SpatialScenarioRequest.model_validate({
        "allocator_type": "huff",
        "candidate_facility_id": "candidate",
        "zones": [{"zone_id": GEO_ID, "quantity_id": demand.id}],
        "facilities": [
            {"facility_id": "candidate", "quantity_id": candidate.id},
            {"facility_id": "competitor", "quantity_id": competitor.id},
        ],
        "travel_time_quantity_ids": {
            GEO_ID: {"candidate": candidate_time.id, "competitor": competitor_time.id}
        },
        "distance_decay_quantity_id": decay.id,
    })

    result = scenarios_api.allocate_scenario_spatial_demand(
        SCENARIO_ID, request, SimpleNamespace(id=OWNER)
    )

    assert result["status"] == "COMPLETED"
    assert result["captured_demand_inr_monthly"] == 80
    assert result["market_share_fraction"] == 0.8
    assert result["input_quantity_ids"]["distance_decay:distance_decay_exponent"] == decay.id


def test_accessibility_scenario_records_missing_road_evidence(monkeypatch):
    longitude = _quantity("site.longitude", 80.9, "degree")
    latitude = _quantity("site.latitude", 25.4, "degree")
    speed = _quantity("routing.speed.residential", 20, "km/hour")
    quantities = _QuantityRepo([longitude, latitude, speed])
    scenarios = _ScenarioRepo()
    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", lambda: scenarios)
    monkeypatch.setattr(scenarios_api, "PostgresGeoUnitRepository", _GeoRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRepository", _SourceRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRecordRepository", _GeometrySourceRecordRepo)
    monkeypatch.setattr(scenarios_api, "PostgresQuantityRepository", lambda: quantities)
    monkeypatch.setattr(scenarios_api, "PostgresRoadGraphRepository", lambda: object())
    request = scenarios_api.AccessibilityScenarioRequest.model_validate({
        "road_graph_source_version_id": "unregistered-road-version",
        "extraction_radius_m": 5000,
        "longitude_quantity_id": longitude.id,
        "latitude_quantity_id": latitude.id,
        "road_speed_scenario_id": "owner-speed-v1",
        "speed_quantity_ids": {"residential": speed.id},
        "thresholds_minutes": [15, 30],
        "corridor_width_m": 1000,
        "model_version": "arthlens-routing-v1",
    })

    result = scenarios_api.calculate_scenario_accessibility(
        SCENARIO_ID, request, SimpleNamespace(id=OWNER)
    )

    assert result["status"] == "INSUFFICIENT_DATA"
    assert any("DS-04 road graph" in issue for issue in result["missing_evidence"])
    assert len(result["assumption_quantity_ids"]) == 4
    assert scenarios.scenarios[SCENARIO_ID]["scenario"]["accessibility"]["status"] == "INSUFFICIENT_DATA"


def test_accessibility_scenario_routes_on_exact_source_graph_and_persists_lineage(monkeypatch):
    longitude = _quantity("site.longitude", 80.9, "degree")
    latitude = _quantity("site.latitude", 25.4, "degree")
    speed = _quantity("routing.speed.residential", 20, "km/hour")
    quantities = _QuantityRepo([longitude, latitude, speed])
    scenarios = _ScenarioRepo()
    graph = RoadGraph(
        nodes={
            "n1": RoadNode("n1", 80.9, 25.4),
            "n2": RoadNode("n2", 80.901, 25.4),
        },
        edges=(
            RoadEdge("e1", "n1", "n2", 100, "residential"),
            RoadEdge("e2", "n2", "n1", 100, "residential"),
        ),
        source_version_ids=frozenset({"road-version-1"}),
    )

    class GraphRepo:
        def extract_local_subgraph(self, **kwargs):
            assert kwargs["source_version_id"] == "road-version-1"
            assert kwargs["site"] == (80.9, 25.4)
            return graph

    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", lambda: scenarios)
    monkeypatch.setattr(scenarios_api, "PostgresGeoUnitRepository", _GeoRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRepository", _ActiveRoadSourceRepo)
    monkeypatch.setattr(scenarios_api, "PostgresSourceRecordRepository", _GeometrySourceRecordRepo)
    monkeypatch.setattr(scenarios_api, "PostgresQuantityRepository", lambda: quantities)
    monkeypatch.setattr(scenarios_api, "PostgresRoadGraphRepository", GraphRepo)
    request = scenarios_api.AccessibilityScenarioRequest.model_validate({
        "road_graph_source_version_id": "road-version-1",
        "extraction_radius_m": 5000,
        "longitude_quantity_id": longitude.id,
        "latitude_quantity_id": latitude.id,
        "road_speed_scenario_id": "owner-speed-v1",
        "speed_quantity_ids": {"residential": speed.id},
        "thresholds_minutes": [15],
        "corridor_width_m": 1000,
        "model_version": "arthlens-routing-v1",
    })

    result = scenarios_api.calculate_scenario_accessibility(
        SCENARIO_ID, request, SimpleNamespace(id=OWNER)
    )

    assert result["status"] == "COMPLETED"
    assert result["source_version_id"] == "road-version-1"
    assert result["catchments"][0]["reachable_node_ids"] == ["n1", "n2"]
    output = quantities.get(result["quantity_ids"]["catchment.site_snap_distance"])
    assert output is not None
    assert output.owner_id == OWNER
    assert set(output.parent_ids) == {
        longitude.id,
        latitude.id,
        speed.id,
        *result["assumption_quantity_ids"].values(),
    }


def test_scenario_policy_endpoint_saves_the_policy_trace(monkeypatch):
    scenarios = _ScenarioRepo()
    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", lambda: scenarios)
    monkeypatch.setattr(
        scenarios_api,
        "evaluate_scheme_eligibility",
        lambda scheme, request, user: {
            "id": "evaluation-1",
            "scheme_id": scheme,
            "outcome": "UNKNOWN",
            "status": "INSUFFICIENT_DATA",
            "official_award_decision": False,
            "trace": {"evidence_gate": "INCOMPLETE"},
        },
    )
    request = scenarios_api.ScenarioPolicyEvaluationRequest.model_validate({
        "scheme_id": "scheme-pilot",
        "rule_key": "eligibility",
        "as_of": TODAY,
        "fact_quantity_ids": {},
    })

    result = scenarios_api.evaluate_scenario_policy(
        SCENARIO_ID, request, SimpleNamespace(id=OWNER)
    )

    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["official_award_decision"] is False
    assert scenarios.scenarios[SCENARIO_ID]["scenario"]["policy_evaluation"]["trace"] == {
        "evidence_gate": "INCOMPLETE"
    }


def test_scenario_comparison_persists_delta_from_saved_ledger_outputs(monkeypatch):
    left_id, right_id = str(uuid.uuid4()), str(uuid.uuid4())
    left_parent = _quantity("finance.assumption.price_per_unit", 100, "INR/count")
    right_parent = _quantity("finance.assumption.price_per_unit", 115, "INR/count")
    left_output = Quantity(
        id=str(uuid.uuid4()), definition_key="finance.result.contribution_margin", value=25,
        unit="INR/count", kind=Kind.CALCULATED, evidence_floor=3, geo_unit_id=GEO_ID,
        resolution=2, as_of=TODAY, parent_ids=(left_parent.id,), owner_id=OWNER,
    )
    right_output = Quantity(
        id=str(uuid.uuid4()), definition_key="finance.result.contribution_margin", value=40,
        unit="INR/count", kind=Kind.CALCULATED, evidence_floor=3, geo_unit_id=GEO_ID,
        resolution=2, as_of=TODAY, parent_ids=(right_parent.id,), owner_id=OWNER,
    )
    records = {
        left_id: {"id": left_id, "owner_id": OWNER, "name": "Left", "scenario": {
            "geo_id": GEO_ID, "calculations": {"quantity_ids": {"contribution_margin": left_output.id}}
        }},
        right_id: {"id": right_id, "owner_id": OWNER, "name": "Right", "scenario": {
            "geo_id": GEO_ID, "calculations": {"quantity_ids": {"contribution_margin": right_output.id}}
        }},
    }
    scenarios = _ScenarioRepo(records)
    quantities = _QuantityRepo([left_parent, right_parent, left_output, right_output])
    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", lambda: scenarios)
    monkeypatch.setattr(scenarios_api, "PostgresQuantityRepository", lambda: quantities)
    request = scenarios_api.ScenarioComparisonRequest(
        left_scenario_id=left_id, right_scenario_id=right_id
    )

    result = scenarios_api.compare_scenarios(request, SimpleNamespace(id=OWNER))

    assert result["status"] == "COMPLETED"
    assert result["metrics"]["financial.contribution_margin"]["delta_right_minus_left"]["value"] == 15
    delta = quantities.get(result["metrics"]["financial.contribution_margin"]["delta_right_minus_left"]["quantity_id"])
    assert delta is not None and delta.parent_ids == (left_output.id, right_output.id)
    assert scenarios.get_comparison_by_id_and_owner(result["id"], OWNER)["metric_results"]["status"] == "COMPLETED"
