"""
Integration tests for FIX 2: Exact Geometry Provenance.

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 9.1, 10.2).
Phase: Phase 2 Final Integration.

Verifies:
1. Boundary API uses exact persisted geometry_source_record_id.
2. No fallback lookup of arbitrary first DS-09 SourceRecord.
3. Verify associated SourceRecord belongs to correct source (DS-09) and exact SourceVersion exists.
4. Returns provenance_available=False if required association is missing, mismatched, or unverified.
5. Preserved existing geometry maintains original provenance association.
"""

from datetime import date
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
)
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    GeoUnitModel,
    SourceModel,
    SourceRecordModel,
    SourceVersionModel,
)
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


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

    # Ensure root nation and state exist
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

    # Teardown: delete created test units to preserve national database count invariants
    with session_factory() as session:
        for uid in created_ids:
            u = session.get(GeoUnitModel, uid)
            if u:
                session.delete(u)
        session.commit()


@pytest.mark.integration
def test_missing_geometry_source_record_returns_provenance_unavailable(api_client, auth_cookie, ensure_hierarchy_and_cleanup):
    """
    Test FIX 2: If a GeoUnit has geometry in PostGIS but geometry_source_record_id is NULL,
    the boundary API must return provenance_available=False and NOT fallback to querying
    arbitrary DS-09 records.
    """
    session_factory = get_session_factory()

    unit_id = f"in:district:test_no_prov_{uuid.uuid4().hex[:6]}"
    lgd_code = str(uuid.uuid4().int)[:5]

    unit = GeoUnit(
        id=unit_id,
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Test District No Prov",
        lgd_code=lgd_code,
        geometry={
            "type": "Polygon",
            "coordinates": [[[80.0, 25.0], [81.0, 25.0], [81.0, 26.0], [80.0, 26.0], [80.0, 25.0]]],
        },
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_HISTORICAL,
        analytical_status=AnalyticalStatus.ANALYSABLE,
        geometry_source_record_id=None,  # No source record foreign key
    )
    ensure_hierarchy_and_cleanup(unit)

    # Also seed an unrelated DS-09 SourceRecord with matching geo_unit_id to verify NO fallback lookup occurs
    with session_factory() as session:
        # Ensure DS-09 source exists
        if not session.get(SourceModel, "DS-09"):
            session.add(SourceModel(id="DS-09", name="Administrative Boundaries", licence_text="GODL", status="ACTIVE"))
            session.flush()

        dummy_ver_id = f"DS-09:dummy_ver_{uuid.uuid4().hex[:6]}"
        sver_dummy = SourceVersionModel(
            id=dummy_ver_id,
            source_id="DS-09",
            version="Dummy Version",
            retrieval_date=date(2026, 1, 1),
            content_hash="9999999999999999999999999999999999999999999999999999999999999999",
            status="ACTIVE",
        )
        session.add(sver_dummy)
        session.flush()

        sr_unrelated = SourceRecordModel(
            id=f"DS-09:unrelated:{uuid.uuid4().hex[:8]}",
            source_id="DS-09",
            source_version_id=dummy_ver_id,
            record_id=f"boundary:{lgd_code}",
            original_fields={},
            normalized_fields={"vintage": "Census 2011"},
            canonical_units={},
            geo_resolved=True,
            geo_unit_id=unit_id,  # Unrelated matching geo_unit_id
            license_name="GODL",
            attribution="Unrelated Attribution",
        )
        session.add(sr_unrelated)
        session.commit()

    # Query boundary API
    res = api_client.get(f"/geo/{unit_id}/boundary", cookies=auth_cookie)
    assert res.status_code == 200
    b = res.json()

    # Invariant: Must report provenance_available = False because geometry_source_record_id is NULL!
    assert b["provenance_available"] is False
    assert b["properties"]["provenance_available"] is False
    assert b["properties"]["source_id"] is None
    assert b["properties"]["source_name"] is None


@pytest.mark.integration
def test_exact_geometry_provenance_verified_with_source_record(api_client, auth_cookie, ensure_hierarchy_and_cleanup):
    """
    Test FIX 2: Exact geometry provenance is returned when geometry_source_record_id
    points to a valid DS-09 SourceRecord and SourceVersion.
    """
    session_factory = get_session_factory()

    unit_id = f"in:district:test_prov_{uuid.uuid4().hex[:6]}"
    lgd_code = str(uuid.uuid4().int)[:5]
    v_id = f"DS-09:ver_{uuid.uuid4().hex[:6]}"
    sr_id = f"{v_id}:boundary:{lgd_code}"
    expected_hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    with session_factory() as session:
        if not session.get(SourceModel, "DS-09"):
            session.add(SourceModel(id="DS-09", name="Administrative Boundaries", licence_text="GODL", status="ACTIVE"))

        sver = SourceVersionModel(
            id=v_id,
            source_id="DS-09",
            version="Census 2011 Pilot",
            retrieval_date=date(2026, 1, 1),
            content_hash=expected_hash,
            status="ACTIVE",
        )
        session.add(sver)

        sr = SourceRecordModel(
            id=sr_id,
            source_id="DS-09",
            source_version_id=v_id,
            record_id=f"boundary:{lgd_code}",
            original_fields={"test": True},
            normalized_fields={"vintage": "Census 2011 Pilot"},
            canonical_units={},
            geo_resolved=True,
            geo_unit_id=unit_id,
            license_name="GODL-India",
            attribution="DataMeet Census 2011 Maps",
        )
        session.add(sr)
        session.commit()

    unit = GeoUnit(
        id=unit_id,
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Test District With Exact Prov",
        lgd_code=lgd_code,
        geometry={
            "type": "Polygon",
            "coordinates": [[[80.0, 25.0], [81.0, 25.0], [81.0, 26.0], [80.0, 26.0], [80.0, 25.0]]],
        },
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_HISTORICAL,
        analytical_status=AnalyticalStatus.ANALYSABLE,
        geometry_source_record_id=sr_id,  # Exact foreign key
    )
    ensure_hierarchy_and_cleanup(unit)

    res = api_client.get(f"/geo/{unit_id}/boundary", cookies=auth_cookie)
    assert res.status_code == 200
    b = res.json()

    # Invariant: Provenance is available and exact
    assert b["provenance_available"] is True
    assert b["properties"]["provenance_available"] is True
    assert b["properties"]["source_id"] == "DS-09"
    assert b["properties"]["source_version_id"] == v_id
    assert b["properties"]["checksum"] == expected_hash
    assert b["properties"]["vintage"] == "Census 2011 Pilot"
    assert b["properties"]["license_name"] == "GODL-India"
    assert b["properties"]["attribution"] == "DataMeet Census 2011 Maps"


@pytest.mark.integration
def test_mismatched_source_record_fails_closed(api_client, auth_cookie, ensure_hierarchy_and_cleanup):
    """
    Test FIX 2: If geometry_source_record_id points to a SourceRecord from a different source
    (not DS-09, e.g. DS-04), provenance verification must fail closed (provenance_available=False).
    """
    session_factory = get_session_factory()

    unit_id = f"in:district:test_mismatch_{uuid.uuid4().hex[:6]}"
    lgd_code = str(uuid.uuid4().int)[:5]
    wrong_sr_id = f"DS-04:node:{uuid.uuid4().hex[:8]}"

    with session_factory() as session:
        if not session.get(SourceModel, "DS-04"):
            session.add(SourceModel(id="DS-04", name="OpenStreetMap", licence_text="ODbL", status="ACTIVE"))

        sver = SourceVersionModel(
            id=f"DS-04:ver_{uuid.uuid4().hex[:6]}",
            source_id="DS-04",
            version="OSM snapshot",
            retrieval_date=date(2026, 1, 1),
            content_hash="3333333333333333333333333333333333333333333333333333333333333333",
            status="ACTIVE",
        )
        session.add(sver)

        sr_wrong = SourceRecordModel(
            id=wrong_sr_id,
            source_id="DS-04",  # WRONG SOURCE! Not administrative boundaries
            source_version_id=sver.id,
            record_id=f"osm:node:{lgd_code}",
            original_fields={},
            normalized_fields={},
            canonical_units={},
            geo_resolved=True,
            geo_unit_id=unit_id,
            license_name="ODbL",
            attribution="OSM contributors",
        )
        session.add(sr_wrong)
        session.commit()

    unit = GeoUnit(
        id=unit_id,
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Test District Mismatch",
        lgd_code=lgd_code,
        geometry={
            "type": "Polygon",
            "coordinates": [[[80.0, 25.0], [81.0, 25.0], [81.0, 26.0], [80.0, 26.0], [80.0, 25.0]]],
        },
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_HISTORICAL,
        analytical_status=AnalyticalStatus.ANALYSABLE,
        geometry_source_record_id=wrong_sr_id,
    )
    ensure_hierarchy_and_cleanup(unit)

    res = api_client.get(f"/geo/{unit_id}/boundary", cookies=auth_cookie)
    assert res.status_code == 200
    b = res.json()
    assert b["provenance_available"] is False
    assert b["properties"]["provenance_available"] is False
