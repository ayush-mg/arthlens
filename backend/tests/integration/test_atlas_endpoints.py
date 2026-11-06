"""
Integration Tests for Atlas, Provenance Drawer, and Evidence Graph Endpoints (P2-4).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 10.2, Part 13.1 P2-4).
Phase: Phase 2 (P2-4 - Interactive Atlas, Provenance Drawer and Evidence Graph).

Acceptance Criterion:
Every displayed number opens its ledger record.

Verifies:
1. /geo/units returns geographic hierarchy units (supports filter by level and search).
2. /geo/pilot-boundaries returns verified Prayagraj boundary GeoJSON.
3. /geo/{id} returns unit details, geometry status, and subunits.
4. /ledger/{quantity_id} returns all required Provenance Drawer fields:
   id, value, unit, kind, evidence_floor, as_of, source_refs, parents, quality, temporal, restrictions.
5. Parent quantity navigation is preserved in ledger responses.
6. /ledger/{quantity_id}/graph returns Cytoscape.js DAG format with claims, quantities, calculations, and sources.
7. Unauthenticated access returns 401.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
)
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresQuantityRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def api_client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_cookie():
    repo = PostgresUserRepository()
    user_id = str(uuid.uuid4())
    email = f"user_{user_id[:8]}@arthlens.org"
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash_atlas_test",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value])
    return {get_auth_cookie_name(): token}


@pytest.fixture
def seeded_quantities_and_geo():
    """Seed test hierarchy and quantities with parent-child ancestry graph."""
    geo_repo = PostgresGeoUnitRepository()
    q_repo = PostgresQuantityRepository()

    # Ensure pilot Prayagraj unit exists in test DB
    nation = GeoUnit(id="in", parent_id=None, level=ResolutionTier.NATION, name="India", lgd_code="IN")
    up = GeoUnit(id="in:state:09", parent_id="in", level=ResolutionTier.STATE, name="Uttar Pradesh", lgd_code="09")
    prayagraj = GeoUnit(
        id="in:district:120",
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Prayagraj",
        lgd_code="120",
        census_code="175",
        geometry={"type": "Polygon", "coordinates": [[[81.52, 24.78], [82.35, 24.78], [82.35, 25.79], [81.52, 25.79], [81.52, 24.78]]]},
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        analytical_status=AnalyticalStatus.ANALYSABLE,
    )
    geo_repo.save_units([nation, up, prayagraj])

    # 1. Parent Quantity: Census 2011 Population (STALE)
    q_pop = Quantity(
        id=str(uuid.uuid4()),
        definition_key="population.total",
        value=5954391.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2011-03-01",
        source_refs=("DS-05",),
        quality_flags=frozenset({"STALE"}),
    )
    q_repo.save(q_pop)

    # 2. Derived Quantity: Monthly Micro-enterprise Demand (ESTIMATED, depends on q_pop)
    q_demand = Quantity(
        id=str(uuid.uuid4()),
        definition_key="demand.monthly",
        value=85000.0,
        unit="INR/month",
        kind=Kind.ESTIMATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-10-01",
        parent_ids=(q_pop.id,),
        method_id="downscaling.gravity_v1",
        license_meta="Downscaled monthly demand projection derived from district census population baseline.",
        quality_flags=frozenset({"STALE_ANCESTRY"}),
    )
    q_repo.save(q_demand)

    return {"prayagraj": prayagraj, "q_pop": q_pop, "q_demand": q_demand}


@pytest.mark.integration
class TestAtlasEndpoints:
    """Tests Atlas geographic navigation and boundary endpoints."""

    def test_get_pilot_boundaries(self, api_client, auth_cookie):
        """GET /geo/pilot-boundaries returns verified GeoJSON FeatureCollection."""
        res = api_client.get("/geo/pilot-boundaries", cookies=auth_cookie)
        assert res.status_code == 200
        geojson = res.json()
        assert geojson.get("type") == "FeatureCollection"
        features = geojson.get("features", [])
        assert len(features) >= 1
        district_feature = next(f for f in features if f["properties"].get("DISTRICT") == "Prayagraj")
        assert district_feature["properties"]["lgd_code"] == "120"
        assert district_feature["geometry"]["type"] == "Polygon"

    def test_list_geo_units_hierarchy(self, api_client, auth_cookie, seeded_quantities_and_geo):
        """GET /geo/units supports level filter and search."""
        # Level 1 (States)
        res_states = api_client.get("/geo/units?level=1", cookies=auth_cookie)
        assert res_states.status_code == 200
        data = res_states.json()
        assert "units" in data
        assert any(u["name"] == "Uttar Pradesh" for u in data["units"])

        # Search for 'Prayagraj'
        res_search = api_client.get("/geo/units?search=Prayagraj", cookies=auth_cookie)
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert len(search_data["units"]) >= 1
        assert search_data["units"][0]["name"] == "Prayagraj"
        assert search_data["units"][0]["id"] == "in:district:120"

    def test_get_geo_unit_details(self, api_client, auth_cookie, seeded_quantities_and_geo):
        """GET /geo/{id} returns unit metadata and parent information."""
        res = api_client.get("/geo/in:district:120", cookies=auth_cookie)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "in:district:120"
        assert data["name"] == "Prayagraj"
        assert data["parent_id"] == "in:state:09"
        assert data["parent_name"] == "Uttar Pradesh"
        assert data["navigation_status"] == "NAVIGABLE"
        assert data["geometry_status"] == "GEOMETRY_VERIFIED"
        assert data["analytical_status"] == "ANALYSABLE"


@pytest.mark.integration
class TestProvenanceAndEvidenceGraphEndpoints:
    """Tests Provenance Drawer and Evidence Graph endpoints."""

    def test_provenance_drawer_payload_contains_all_fields(
        self, api_client, auth_cookie, seeded_quantities_and_geo
    ):
        """
        Acceptance Criterion: Every displayed number opens its ledger record.
        GET /ledger/{quantity_id} returns all required Provenance Drawer fields.
        """
        q_pop = seeded_quantities_and_geo["q_pop"]
        res = api_client.get(f"/ledger/{q_pop.id}", cookies=auth_cookie)
        assert res.status_code == 200
        p = res.json()

        # 1. Quantity identification and value
        assert p["id"] == q_pop.id
        assert p["definition_key"] == "population.total"
        assert p["value"] == 5954391.0
        assert p["unit"] == "persons"
        assert p["kind"] == "OBSERVED"
        assert p["evidence_floor"] == 4
        assert p["resolution"] == 2

        # 2. Temporal & staleness metadata
        assert p["as_of"] == "2011-03-01"
        assert "STALE" in p["quality_flags"]
        assert p["temporal"]["as_of"] == "2011-03-01"
        assert p["temporal"]["has_policy"] is True
        assert p["temporal"]["max_age_days"] == 3650

        # 3. Quality evaluation
        assert p["quality"]["primary_status"] == "STALE"
        assert p["quality"]["shading"]["hex_color"] == "#F97316"
        assert any("Historical Only" in r for r in p["calculation_restrictions"])

    def test_parent_quantity_navigation_in_provenance_drawer(
        self, api_client, auth_cookie, seeded_quantities_and_geo
    ):
        """Derived quantity returns parent quantities enabling navigation in Provenance Drawer."""
        q_demand = seeded_quantities_and_geo["q_demand"]
        q_pop = seeded_quantities_and_geo["q_pop"]

        res = api_client.get(f"/ledger/{q_demand.id}", cookies=auth_cookie)
        assert res.status_code == 200
        p = res.json()

        assert p["kind"] == "ESTIMATED"
        assert p["method_id"] == "downscaling.gravity_v1"
        assert "Downscaled monthly demand" in (p.get("license_meta") or p.get("assumptions") or "")
        assert len(p["parents"]) == 1
        assert p["parents"][0]["id"] == q_pop.id
        assert p["parents"][0]["definition_key"] == "population.total"
        assert p["parents"][0]["value"] == 5954391.0
        assert p["parents"][0]["quality_status"] == "STALE"

    def test_evidence_graph_cytoscape_dag_structure(
        self, api_client, auth_cookie, seeded_quantities_and_geo
    ):
        """GET /ledger/{quantity_id}/graph returns valid Cytoscape.js DAG format."""
        q_demand = seeded_quantities_and_geo["q_demand"]
        q_pop = seeded_quantities_and_geo["q_pop"]

        res = api_client.get(f"/ledger/{q_demand.id}/graph", cookies=auth_cookie)
        assert res.status_code == 200
        graph = res.json()

        assert graph["root_quantity_id"] == q_demand.id
        elements = graph["elements"]
        nodes = elements["nodes"]
        edges = elements["edges"]

        node_ids = {n["data"]["id"] for n in nodes}
        node_types = {n["data"]["type"] for n in nodes}

        # Must contain Quantity nodes, Claim node, and Calculation node
        assert q_demand.id in node_ids
        assert q_pop.id in node_ids
        assert "quantity" in node_types
        assert "claim" in node_types
        assert "calculation" in node_types

        # Edges connect parent -> calculation -> derived quantity -> claim
        assert len(edges) >= 3
        edge_types = {e["data"]["type"] for e in edges}
        assert "derives_from" in edge_types
        assert "calculates" in edge_types
        assert "supports_claim" in edge_types

    def test_unauthenticated_request_rejected(self, api_client):
        """Protected endpoints reject unauthenticated calls with 401."""
        assert api_client.get("/geo/pilot-boundaries").status_code == 401
        assert api_client.get("/geo/units").status_code == 401
        assert api_client.get("/geo/in:district:120").status_code == 401
        assert api_client.get(f"/ledger/{uuid.uuid4()}").status_code == 401
        assert api_client.get(f"/ledger/{uuid.uuid4()}/graph").status_code == 401

    def test_complete_number_to_ledger_interaction_flow(
        self, api_client, auth_cookie, seeded_quantities_and_geo
    ):
        """
        Acceptance Invariant: Every displayed number opens its ledger record.
        1. Fetch actual indicators for a district through backend.
        2. Verify returned factual values and their quantity IDs.
        3. Query ledger record for the clicked quantity.
        4. Verify complete epistemic attributes (value, unit, kind, source, quality, assumptions, ancestry).
        """
        q_pop = seeded_quantities_and_geo["q_pop"]
        q_demand = seeded_quantities_and_geo["q_demand"]

        # Step 1: Fetch indicators for Prayagraj
        res_ind = api_client.get("/geo/in:district:120/indicators", cookies=auth_cookie)
        assert res_ind.status_code == 200
        ind_data = res_ind.json()
        indicators = ind_data["indicators"]
        assert len(indicators) >= 2

        # Step 2: Locate demand indicator and verify factual value
        demand_ind = next(item for item in indicators if item["id"] == q_demand.id)
        assert demand_ind["definition_key"] == "demand.monthly"
        assert demand_ind["value"] == 85000.0
        assert demand_ind["unit"] == "INR/month"
        assert demand_ind["kind"] == "ESTIMATED"
        assert demand_ind["quality_status"] == "ESTIMATED"

        # Step 3: Click value -> Query actual ledger record
        res_ledger = api_client.get(f"/ledger/{demand_ind['id']}", cookies=auth_cookie)
        assert res_ledger.status_code == 200
        ledger = res_ledger.json()

        # Step 4: Verify complete epistemic ledger attributes
        assert ledger["id"] == q_demand.id
        assert ledger["definition_key"] == "demand.monthly"
        assert ledger["value"] == 85000.0
        assert ledger["unit"] == "INR/month"
        assert ledger["kind"] == "ESTIMATED"
        assert ledger["evidence_floor"] == 2
        assert ledger["method_id"] == "downscaling.gravity_v1"
        assert "Downscaled monthly demand" in ledger["assumptions"]
        assert ledger["quality"]["primary_status"] == "ESTIMATED"
        assert ledger["quality"]["shading"]["hex_color"] == "#3B82F6"

        # Verify parent ancestry
        assert len(ledger["parents"]) == 1
        parent = ledger["parents"][0]
        assert parent["id"] == q_pop.id
        assert parent["definition_key"] == "population.total"
        assert parent["value"] == 5954391.0
        assert parent["unit"] == "persons"
        assert parent["quality_status"] == "STALE"

        # Verify calculation restrictions are actively exposed
        assert any("Estimated Projection" in r for r in ledger["calculation_restrictions"])
        assert any("Stale Ancestry" in r for r in ledger["calculation_restrictions"])

    def test_unavailable_value_invariant_never_becomes_zero(
        self, api_client, auth_cookie, seeded_quantities_and_geo
    ):
        """
        Acceptance Invariant: Unavailable values never become numeric zero.
        When an indicator has not been observed or ingested, quality evaluation
        strictly returns UNAVAILABLE and never fabricates numeric 0 or 0.0.
        """
        # Query quality for an indicator not present in the database
        res_quality = api_client.get(
            "/geo/in:district:120/quality?indicator=agriculture.soil_fertility_index",
            cookies=auth_cookie,
        )
        assert res_quality.status_code == 200
        quality = res_quality.json()
        assert quality["primary_status"] == "UNAVAILABLE"
        assert quality["shading"]["hex_color"] == "#94A3B8"
        assert quality["suitability"] == "UNSUITABLE_MISSING"

        # Verify indicator list for districts with no quantities does not synthesize zeros
        res_empty = api_client.get("/geo/in:district:187/indicators", cookies=auth_cookie)
        assert res_empty.status_code == 200
        indicators = res_empty.json()["indicators"]
        assert all(item["value"] is None for item in indicators)
        assert all(item["quality_status"] == "UNAVAILABLE" for item in indicators)

    def test_clean_database_absent_evidence_produces_unavailable_indicator(
        self, api_client, auth_cookie, seeded_quantities_and_geo
    ):
        """
        Acceptance Invariant: Clean-database absent evidence produces UNAVAILABLE, never fabricated numbers.
        For an unobserved district (in:district:187 Varanasi), verifies:
        1. All core indicators are returned with value: None (never numeric zero 0 or 0.0).
        2. Quality status is strictly UNAVAILABLE with slate shading (#94A3B8).
        3. No demonstration economic numbers (85000, 5954391, 142, 1073284) appear.
        4. Every returned unavailable indicator ID opens its epistemic data-gap ledger record.
        """
        res = api_client.get("/geo/in:district:187/indicators", cookies=auth_cookie)
        assert res.status_code == 200
        indicators = res.json()["indicators"]
        assert len(indicators) >= 5

        # Check every indicator
        for item in indicators:
            # Must NEVER be numeric zero or any number
            assert item["value"] is None
            assert item["value"] != 0
            assert item["value"] != 0.0

            # Must be strictly UNAVAILABLE
            assert item["quality_status"] == "UNAVAILABLE"
            assert item["shading"]["hex_color"] == "#94A3B8"
            assert item["suitability"] == "UNSUITABLE_MISSING"

            # Must have valid structured quantity ID
            assert item["id"].startswith("unavailable:in:district:187:")

            # Every displayed indicator opens its ledger record
            res_ledger = api_client.get(f"/ledger/{item['id']}", cookies=auth_cookie)
            assert res_ledger.status_code == 200
            ledger = res_ledger.json()
            assert ledger["id"] == item["id"]
            assert ledger["value"] is None
            assert ledger["quality"]["primary_status"] == "UNAVAILABLE"
            assert any("Unavailable Evidence" in r for r in ledger["calculation_restrictions"])

    def test_invalid_quantity_reference_fails_closed(self, api_client, auth_cookie):
        """
        Acceptance Invariant: Missing or invalid quantity references cannot silently open an unrelated record.
        Unknown quantity queries must return 404 Not Found.
        """
        fake_id = str(uuid.uuid4())
        res_ledger = api_client.get(f"/ledger/{fake_id}", cookies=auth_cookie)
        assert res_ledger.status_code == 404
        assert res_ledger.json()["detail"] == "Quantity not found."

        res_graph = api_client.get(f"/ledger/{fake_id}/graph", cookies=auth_cookie)
        assert res_graph.status_code == 404
        assert res_graph.json()["detail"] == "Quantity not found."
