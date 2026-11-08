"""
Integration tests for FIX 3: Real Atlas Quality Integration.

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 7.5, 10.2).
Phase: Phase 2 Final Integration.

Verifies:
1. Provide an active indicator selection via /geo/{geo_id}/boundary?indicator={indicator_key}.
2. Retrieve the selected indicator's actual quality assessments from the backend.
3. GeoJSON properties contain genuine quality_status and indicator_quality.
4. No quality choropleth when no indicator is selected (indicator_quality=None).
5. Preserve quality independence from geometry availability.
6. Do not shade missing geometry as though it has an analytical quality result.
7. Only shade actual persisted and appropriately approved geometries.
"""

import uuid
from datetime import date

import pytest
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
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import GeoUnitModel, SourceModel, SourceVersionModel
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresQuantityRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    return TestClient(create_app())


@pytest.fixture
def auth_cookie():
    repo = PostgresUserRepository()
    user_id = str(uuid.uuid4())
    email = f"user_{user_id[:8]}@arthlens.org"
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value])
    return {get_auth_cookie_name(): token}


@pytest.fixture
def ensure_hierarchy_and_cleanup():
    """Ensure parent units exist and clean up created test units after test."""
    geo_repo = PostgresGeoUnitRepository()
    session_factory = get_session_factory()
    created_ids = []

    with session_factory() as session:
        if not session.get(GeoUnitModel, "in"):
            session.add(GeoUnitModel(id="in", level=0, name="India", coverage_status="NAVIGABLE", geometry_status="GEOMETRY_MISSING", analytical_status="ANALYSIS_UNAVAILABLE"))
        if not session.get(GeoUnitModel, "in:state:09"):
            session.add(GeoUnitModel(id="in:state:09", parent_id="in", level=1, name="Uttar Pradesh", lgd_code="09", coverage_status="NAVIGABLE", geometry_status="GEOMETRY_MISSING", analytical_status="ANALYSIS_UNAVAILABLE"))
        session.commit()

    def register_test_unit(unit: GeoUnit):
        created_ids.append(unit.id)
        geo_repo.save_unit(unit)
        return unit

    yield register_test_unit

    with session_factory() as session:
        for uid in created_ids:
            u = session.get(GeoUnitModel, uid)
            if u:
                session.delete(u)
        session.commit()


@pytest.mark.integration
def test_atlas_boundary_active_indicator_quality_flow(api_client, auth_cookie, ensure_hierarchy_and_cleanup):
    """
    Test FIX 3: Genuine backend quality assessment flows directly into boundary GeoJSON properties
    when an active indicator is selected.
    """
    q_repo = PostgresQuantityRepository()

    unit_id = f"in:district:test_atlas_flow_{uuid.uuid4().hex[:6]}"
    lgd_code = str(uuid.uuid4().int)[:5]

    unit = GeoUnit(
        id=unit_id,
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Test Atlas District",
        lgd_code=lgd_code,
        geometry={
            "type": "Polygon",
            "coordinates": [[[81.0, 25.0], [82.0, 25.0], [82.0, 26.0], [81.0, 26.0], [81.0, 25.0]]],
        },
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_HISTORICAL,
        analytical_status=AnalyticalStatus.ANALYSABLE,
    )
    ensure_hierarchy_and_cleanup(unit)

    # Seed an empirical observed quantity with STALE quality
    q_id = str(uuid.uuid4())
    source_version_id = f"DS-05:atlas-test:{q_id}"
    with get_session_factory()() as session:
        if session.get(SourceModel, "DS-05") is None:
            session.add(
                SourceModel(
                    id="DS-05",
                    name="Census of India 2011",
                    description="Test source registration for quality integration",
                    licence_text="GODL-India",
                    status="ACTIVE",
                )
            )
        session.add(
            SourceVersionModel(
                id=source_version_id,
                source_id="DS-05",
                version="2011-test",
                retrieval_date=date(2012, 1, 1),
                content_hash="b" * 64,
                status="ACTIVE",
            )
        )
        session.commit()
    q = Quantity(
        id=q_id,
        definition_key="population.total",
        value=1234567.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id=unit_id,
        resolution=2,
        as_of="2011-03-01",
        source_refs=((source_version_id, "Census-table:row:1", "2012-01-01"),),
        quality_flags=frozenset({"STALE"}),
    )
    q_repo.save(q)

    # 1. Query boundary WITH active indicator
    res = api_client.get(f"/geo/{unit_id}/boundary?indicator=population.total", cookies=auth_cookie)
    assert res.status_code == 200
    b = res.json()

    assert b["has_geometry"] is True
    assert len(b["features"]) == 1
    feat_props = b["features"][0]["properties"]

    # Invariant: Quality assessment reached the Atlas feature properties
    assert feat_props["quality_status"] == "STALE"
    assert feat_props["indicator_quality"] is not None
    assert feat_props["indicator_quality"]["primary_status"] == "STALE"
    assert feat_props["indicator_quality"]["shading"]["hex_color"] == "#F97316"
    assert b["properties"]["quality_status"] == "STALE"

    # 2. Query boundary WITHOUT indicator (no indicator selected)
    res_no_ind = api_client.get(f"/geo/{unit_id}/boundary", cookies=auth_cookie)
    assert res_no_ind.status_code == 200
    b_no_ind = res_no_ind.json()

    # Invariant: No quality choropleth when no indicator selected
    assert b_no_ind["features"][0]["properties"]["indicator_quality"] is None
    assert b_no_ind["features"][0]["properties"]["quality_status"] is None


@pytest.mark.integration
def test_missing_geometry_never_shaded_with_quality_choropleth(api_client, auth_cookie, ensure_hierarchy_and_cleanup):
    """
    Test FIX 3: Units with GEOMETRY_MISSING return has_geometry=False and 0 features.
    They are NEVER shaded as though they have an analytical boundary geometry.
    """
    unit_id = f"in:district:test_missing_geom_{uuid.uuid4().hex[:6]}"
    lgd_code = str(uuid.uuid4().int)[:5]

    unit = GeoUnit(
        id=unit_id,
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Test Missing District",
        lgd_code=lgd_code,
        geometry=None,
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_MISSING,
        analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
    )
    ensure_hierarchy_and_cleanup(unit)

    res = api_client.get(f"/geo/{unit_id}/boundary?indicator=population.total", cookies=auth_cookie)
    assert res.status_code == 200
    b = res.json()

    # Invariant: Missing geometry returns 0 features and has_geometry=False
    assert b["has_geometry"] is False
    assert len(b["features"]) == 0
    assert b["geometry_status"] == "GEOMETRY_MISSING"

