"""
Integration Tests for Administrative Boundary Ingestion Pipeline and Dynamic Boundary API.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, Part 10, Part 13.1 P2-4).
Phase: Phase 2 (P2-4 - Administrative Boundary PostGIS Pipeline and Dynamic Dynamic Boundary Service).

Verifies:
1. Multistage national hierarchy + boundary enrichment flow.
2. Boundary ingestion idempotency and duplicate rejection.
3. Topological validity via Shapely and PostGIS ST_IsValid.
4. Detection and rejection of artificial axis-aligned bounding boxes (AABBs).
5. Ring coordinate validation (numeric bounds [-180, 180], [-90, 90], closed ring invariants).
6. Preservation of existing valid geometry when incomplete or null geometry is presented.
7. Dynamic Boundary API (GET /geo/{geo_id}/boundary):
   - 401 Unauthorized for unauthenticated requests.
   - 200 OK for Prayagraj (in:district:120) with verified boundary, DS-09 provenance, and 1 feature.
   - 200 OK for Varanasi (in:district:187), Bhopal (in:district:396), Jaipur (in:district:102) with
     deterministic empty features (0 features), GEOMETRY_MISSING, and has_geometry=False.
   - 404 Not Found for unknown geographic identifiers (in:district:999999).
8. Backward compatibility of GET /geo/pilot-boundaries.
9. Coverage summary metrics and DS-09 source registration in PostgreSQL.
"""

import json
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.data.adapters.admin_boundaries import (
    AdminBoundariesAdapter,
    AdminBoundaryIngestionService,
    is_axis_aligned_bounding_box,
    validate_boundary_geometry,
    validate_ring_coordinates,
)
from backend.arthlens.data.geo_loader import LGDHierarchyLoader, init_national_database
from backend.arthlens.domain.geo import GeometryStatus
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
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
    email = f"boundary_tester_{user_id[:8]}@arthlens.org"
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash_boundary_test",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(
        user_id=user_id,
        email=email,
        roles=[Role.ENTREPRENEUR.value],
    )
    cookie_name = get_auth_cookie_name()
    return {cookie_name: token}


class TestAdministrativeBoundaryIngestionPipeline:
    """Verifies PostGIS boundary ingestion pipeline and validation integrity."""

    def test_rejection_of_axis_aligned_bounding_box(self):
        """Synthetic rectangular bounding boxes must be detected and rejected."""
        bbox_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [81.52, 24.78],
                    [82.35, 24.78],
                    [82.35, 25.79],
                    [81.52, 25.79],
                    [81.52, 24.78],
                ]
            ],
        }
        assert is_axis_aligned_bounding_box(bbox_polygon) is True

        # Realistic non-rectangular boundary polygon with 7 coordinates
        real_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [81.52, 24.80],
                    [81.70, 24.85],
                    [82.00, 24.90],
                    [82.35, 25.20],
                    [82.20, 25.75],
                    [81.90, 25.70],
                    [81.52, 24.80],
                ]
            ],
        }
        assert is_axis_aligned_bounding_box(real_polygon) is False

    def test_ring_coordinates_validation_invariants(self):
        """Ring coordinate validator must enforce coordinate ranges and ring closure."""
        # Unclosed ring
        errs_unclosed: list[str] = []
        assert validate_ring_coordinates([
            [81.5, 24.8],
            [82.0, 24.8],
            [82.0, 25.5],
            [81.5, 25.0],
        ], errors=errs_unclosed) is False
        assert any("not closed" in e for e in errs_unclosed)

        # Too few points
        errs_few: list[str] = []
        assert validate_ring_coordinates([
            [81.5, 24.8],
            [82.0, 24.8],
            [81.5, 24.8],
        ], errors=errs_few) is False
        assert any("at least 4 positions" in e for e in errs_few)

        # Out-of-bounds longitude
        errs_lon: list[str] = []
        assert validate_ring_coordinates([
            [185.0, 24.8],
            [82.0, 24.8],
            [82.0, 25.5],
            [185.0, 24.8],
        ], errors=errs_lon) is False
        assert any("longitude" in e and "outside [-180, 180]" in e for e in errs_lon)

        # Out-of-bounds latitude
        errs_lat: list[str] = []
        assert validate_ring_coordinates([
            [81.5, 95.0],
            [82.0, 24.8],
            [82.0, 25.5],
            [81.5, 95.0],
        ], errors=errs_lat) is False
        assert any("latitude" in e and "outside [-90, 90]" in e for e in errs_lat)

        # Valid ring
        valid_ring = [
            [81.52, 24.80],
            [81.70, 24.85],
            [82.00, 24.90],
            [82.35, 25.20],
            [82.20, 25.75],
            [81.90, 25.70],
            [81.52, 24.80],
        ]
        assert validate_ring_coordinates(valid_ring) is True

    def test_topological_validity_via_postgis_st_isvalid(self):
        """Geometries must be topologically verified using PostGIS ST_IsValid."""
        repo = PostgresGeoUnitRepository()

        # Valid multi-vertex polygon
        valid_geojson = {
            "type": "Polygon",
            "coordinates": [
                [
                    [81.52, 24.80],
                    [81.70, 24.85],
                    [82.00, 24.90],
                    [82.35, 25.20],
                    [82.20, 25.75],
                    [81.90, 25.70],
                    [81.52, 24.80],
                ]
            ],
        }
        is_valid, reason = repo.verify_geometry_validity(valid_geojson)
        assert is_valid is True
        assert reason == "Valid Geometry"

        # Invalid self-intersecting hourglass / bowtie polygon
        invalid_bowtie = {
            "type": "Polygon",
            "coordinates": [
                [
                    [0.0, 0.0],
                    [1.0, 1.0],
                    [0.0, 1.0],
                    [1.0, 0.0],
                    [0.0, 0.0],
                ]
            ],
        }
        is_valid_bowtie, reason_bowtie = repo.verify_geometry_validity(invalid_bowtie)
        assert is_valid_bowtie is False
        assert "Self-intersection" in reason_bowtie

    def test_multistage_initialization_flow(self):
        """Multistage initialization executes Stage 1 (hierarchy), Stage 2 (boundaries), and Stage 3 (coverage)."""
        report = init_national_database()
        assert report.total_units == 7721
        assert report.state_count == 36
        assert report.district_count == 763
        assert report.subdistrict_count == 6921

        # Stage 2 boundary reconciliation result
        assert report.boundary_result is not None
        assert report.boundary_result.reconciled_count >= 1
        assert "DS-09" in report.boundary_result.source_id

        # Stage 3 coverage summary
        assert report.coverage_summary is not None
        assert report.coverage_summary["total_units"] == 7721
        assert report.coverage_summary["units_with_geometry"] >= 1
        assert report.coverage_summary["units_missing_geometry"] >= 7720
        assert "GEOMETRY_VERIFIED" in report.coverage_summary["geometry_status_breakdown"]
        assert "GEOMETRY_MISSING" in report.coverage_summary["geometry_status_breakdown"]

    def test_idempotency_of_boundary_ingestion(self):
        """Re-running administrative boundary ingestion must be idempotent and non-destructive."""
        service = AdminBoundaryIngestionService()
        result1 = service.ingest()
        assert result1.reconciled_count >= 1

        result2 = service.ingest()
        assert result2.reconciled_count >= 1
        assert result2.duplicate_count == 0

        repo = PostgresGeoUnitRepository()
        unit = repo.get_by_id("in:district:120")
        assert unit is not None
        assert unit.geometry_status == GeometryStatus.GEOMETRY_VERIFIED
        assert unit.geometry is not None

    def test_preservation_of_valid_geometry(self):
        """Existing valid geometry must not be overwritten when preserve_existing=True and geometry is missing/null."""
        repo = PostgresGeoUnitRepository()
        unit_before = repo.get_by_id("in:district:120")
        assert unit_before is not None
        assert unit_before.geometry is not None

        # Attempt to overwrite with None / GEOMETRY_MISSING
        repo.update_geometry(
            unit_id="in:district:120",
            geometry=None,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
            preserve_existing=True,
        )

        unit_after = repo.get_by_id("in:district:120")
        assert unit_after is not None
        # Geometry must remain intact because preserve_existing is True
        assert unit_after.geometry is not None
        assert unit_after.geometry_status == GeometryStatus.GEOMETRY_VERIFIED

    def test_unsupported_geometry_types_rejected(self):
        """Points, LineStrings, MultiPoints, MultiLineStrings, and GeometryCollections must be rejected."""
        unsupported_geoms = [
            {"type": "Point", "coordinates": [81.84, 25.43]},
            {"type": "LineString", "coordinates": [[81.5, 24.8], [82.0, 25.5]]},
            {"type": "MultiPoint", "coordinates": [[81.5, 24.8], [82.0, 25.5]]},
            {"type": "MultiLineString", "coordinates": [[[81.5, 24.8], [82.0, 25.5]]]},
            {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "Point", "coordinates": [81.84, 25.43]},
                ],
            },
        ]
        adapter = AdminBoundariesAdapter()
        for g in unsupported_geoms:
            is_valid, errs = validate_boundary_geometry(g)
            assert is_valid is False
            assert any("unsupported" in e.lower() for e in errs)

            # Also verify adapter.validate_schema rejects it inside a Feature
            payload = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"lgd_code": "120"},
                        "geometry": g,
                    }
                ],
            }
            s_valid, s_errs = adapter.validate_schema(payload)
            assert s_valid is False
            assert len(s_errs) > 0

    def test_valid_polygon_and_multipolygon_accepted(self):
        """Valid Polygon and MultiPolygon geometries must pass validation."""
        valid_poly = {
            "type": "Polygon",
            "coordinates": [
                [
                    [81.52, 24.80],
                    [81.70, 24.85],
                    [82.00, 24.90],
                    [82.35, 25.20],
                    [82.20, 25.75],
                    [81.90, 25.70],
                    [81.52, 24.80],
                ]
            ],
        }
        is_p_valid, p_errs = validate_boundary_geometry(valid_poly)
        assert is_p_valid is True
        assert len(p_errs) == 0

        valid_multipoly = {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [81.52, 24.80],
                        [81.70, 24.85],
                        [82.00, 24.90],
                        [82.35, 25.20],
                        [82.20, 25.75],
                        [81.90, 25.70],
                        [81.52, 24.80],
                    ]
                ]
            ],
        }
        is_mp_valid, mp_errs = validate_boundary_geometry(valid_multipoly)
        assert is_mp_valid is True
        assert len(mp_errs) == 0

    def test_generic_pipeline_bypass_prevention(self):
        """Generic ingestion pipeline must reject missing geometry status and non-areal geometries."""
        from backend.arthlens.data.models import GeographicReconciliation, NormalizedRecord, RawRecord
        from backend.arthlens.data.pipeline import DatasetIngestionPipeline
        from backend.arthlens.domain.enums import ResolutionTier

        repo = PostgresGeoUnitRepository()
        unit_before = repo.get_by_id("in:district:187")  # Varanasi (no geometry)
        assert unit_before is not None
        assert unit_before.geometry is None

        pipeline = DatasetIngestionPipeline(adapter=AdminBoundariesAdapter(), geo_repo=repo)

        # 1. Attempt to ingest with missing geometry_status (must not default to GEOMETRY_VERIFIED)
        raw_rec = RawRecord(record_id="raw_1", source_id="DS-09", payload={"test": 1})
        nr_missing_status = NormalizedRecord(
            record_id="bypass_test_1",
            raw_record=raw_rec,
            original_fields={},
            normalized_fields={
                "geometry": {
                    "type": "Point",
                    "coordinates": [82.97, 25.31],
                },
                # Notice: geometry_status is omitted
            },
        )
        recon = GeographicReconciliation(
            resolved=True,
            geo_unit_id="in:district:187",
            resolution_tier=ResolutionTier.DISTRICT,
        )

        pipeline._persist_with_session(
            session=None,  # Not inside session
            version_info=type("SourceVersionInfo", (), {"version_id": "test:v1", "content_hash": "abc", "version_tag": "1", "retrieval_date": None})(),
            norm_records=[nr_missing_status],
            reconciliations=[recon],
            quantities=[],
        )

        # Unit must still have no geometry
        unit_after = repo.get_by_id("in:district:187")
        assert unit_after.geometry is None
        assert unit_after.geometry_status == GeometryStatus.GEOMETRY_MISSING

    def test_atomic_provenance_failure_rollback(self, monkeypatch):
        """Failure injection forcing SourceRecord persistence to fail after geometry update rolls back changes and leaves 0 persisted count."""
        from sqlalchemy.orm import Session
        from backend.arthlens.infra.models import SourceRecordModel

        service = AdminBoundaryIngestionService()
        repo = PostgresGeoUnitRepository()

        # Clean existing SourceRecord for DS-09 so creation is guaranteed to execute
        with service.session_factory() as session:
            with session.begin():
                session.query(SourceRecordModel).filter(SourceRecordModel.source_id == "DS-09").delete()

        # Record Prayagraj geometry before test
        unit_before = repo.get_by_id("in:district:120")
        assert unit_before is not None
        assert unit_before.geometry is not None

        # Monkeypatch Session.add to raise an error specifically when adding SourceRecordModel
        orig_add = Session.add

        def fail_add(self, instance, *args, **kwargs):
            if isinstance(instance, SourceRecordModel):
                raise RuntimeError("Injected provenance storage constraint violation")
            return orig_add(self, instance, *args, **kwargs)

        monkeypatch.setattr(Session, "add", fail_add)

        # Run boundary ingestion with failure injected
        report = service.ingest()

        # Invariants:
        # 1. Report must explicitly register failure and 0 persisted geometries
        assert report.success is False
        assert report.persisted_geometries == 0
        assert report.status_counts == {}
        assert any("Atomic boundary persistence failure" in a for a in report.anomalies)

        # 2. Existing valid geometry in PostGIS must remain completely intact
        unit_after = repo.get_by_id("in:district:120")
        assert unit_after is not None
        assert unit_after.geometry is not None
        assert unit_after.geometry_status == GeometryStatus.GEOMETRY_VERIFIED

        # Undo failure injection and restore genuine record for subsequent tests
        monkeypatch.undo()
        restore_rep = service.ingest()
        assert restore_rep.success is True

    def test_postgres_repository_geometry_invariants(self):
        """PostgresGeoUnitRepository enforces consistent PostGIS and domain invariants."""
        repo = PostgresGeoUnitRepository()

        valid_poly = {
            "type": "Polygon",
            "coordinates": [[[81.52, 24.80], [82.35, 24.80], [82.35, 25.75], [81.52, 25.75], [81.52, 24.80]]],
        }

        # 1. Storing non-null geometry with GEOMETRY_MISSING must return False
        assert repo.update_geometry(
            unit_id="in:district:187",
            geometry=valid_poly,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        ) is False

        # 2. Storing None geometry with GEOMETRY_VERIFIED must return False
        assert repo.update_geometry(
            unit_id="in:district:187",
            geometry=None,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        ) is False

        # 3. Non-areal geometry (Point, LineString) must return False
        assert repo.update_geometry(
            unit_id="in:district:187",
            geometry={"type": "Point", "coordinates": [82.97, 25.31]},
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        ) is False

        # 4. Topologically invalid geometry (self-intersecting bowtie) must return False
        invalid_bowtie = {
            "type": "Polygon",
            "coordinates": [[[81.5, 24.8], [82.3, 25.7], [81.5, 25.7], [82.3, 24.8], [81.5, 24.8]]],
        }
        assert repo.update_geometry(
            unit_id="in:district:187",
            geometry=invalid_bowtie,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        ) is False

        # 5. Weaker candidate geometry must not overwrite existing GEOMETRY_VERIFIED when preserve_existing=True
        assert repo.update_geometry(
            unit_id="in:district:120",
            geometry=valid_poly,
            geometry_status=GeometryStatus.GEOMETRY_HISTORICAL,
            preserve_existing=True,
        ) is False


class TestDynamicGeographicBoundaryAPI:
    """Verifies dynamic boundary API endpoint GET /geo/{geo_id}/boundary."""

    def test_boundary_endpoint_requires_authentication(self, api_client):
        """Unauthenticated requests must be rejected with HTTP 401."""
        response = api_client.get("/geo/in:district:120/boundary")
        assert response.status_code == 401

    def test_boundary_endpoint_prayagraj_verified(self, api_client, auth_cookie):
        """Known district with verified PostGIS geometry returns 1 feature and DS-09 provenance."""
        response = api_client.get("/geo/in:district:120/boundary", cookies=auth_cookie)
        assert response.status_code == 200

        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert data["geo_id"] == "in:district:120"
        assert data["has_geometry"] is True
        assert data["geometry_status"] == "GEOMETRY_VERIFIED"
        assert len(data["features"]) == 1

        feature = data["features"][0]
        assert feature["id"] == "in:district:120"
        assert feature["geometry"]["type"] in ("Polygon", "MultiPolygon")
        assert len(feature["geometry"]["coordinates"][0]) >= 4

        props = feature["properties"]
        assert props["lgd_code"] == "120"
        assert props["name"] == "Prayagraj"
        assert props["geometry_status"] == "GEOMETRY_VERIFIED"
        assert props["source_id"] == "DS-09"
        assert "source_name" in props or "publisher" in props
        assert "license_name" in props or "licence" in props
        assert "vintage" in props

    def test_boundary_endpoint_unmapped_districts_return_empty_feature_collection(
        self, api_client, auth_cookie
    ):
        """Known districts without geometry return 0 features and GEOMETRY_MISSING without fabrication."""
        districts_to_test = [
            ("in:district:187", "187", "Varanasi"),
            ("in:district:396", "396", "Bhopal"),
            ("in:district:102", "102", "Jaipur"),
        ]

        for geo_id, lgd_code, name in districts_to_test:
            response = api_client.get(f"/geo/{geo_id}/boundary", cookies=auth_cookie)
            assert response.status_code == 200, f"Expected 200 for {name} ({geo_id})"

            data = response.json()
            assert data["type"] == "FeatureCollection"
            assert data["geo_id"] == geo_id
            assert data["has_geometry"] is False
            assert data["geometry_status"] == "GEOMETRY_MISSING"
            assert len(data["features"]) == 0, f"Expected 0 features for unmapped district {name}"
            assert "detail" in data

    def test_boundary_endpoint_unknown_unit_returns_404(self, api_client, auth_cookie):
        """Non-existent geographic unit must return 404 Not Found."""
        response = api_client.get("/geo/in:district:999999/boundary", cookies=auth_cookie)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_backward_compatible_pilot_boundaries(self, api_client, auth_cookie):
        """Existing /geo/pilot-boundaries endpoint remains fully operational for backward compatibility."""
        response = api_client.get("/geo/pilot-boundaries", cookies=auth_cookie)
        assert response.status_code == 200

        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) >= 1
        assert any(f["properties"].get("lgd_code") == "120" for f in data["features"])

    def test_unmapped_district_has_no_provenance_invention(self, api_client, auth_cookie):
        """Unmapped unit with missing geometry must return None / False for provenance fields, never invented defaults."""
        response = api_client.get("/geo/in:district:187/boundary", cookies=auth_cookie)
        assert response.status_code == 200

        data = response.json()
        props = data["properties"]
        assert props["has_geometry"] is False
        assert props["geometry_status"] == "GEOMETRY_MISSING"
        assert props["provenance_available"] is False
        assert props["source_id"] is None
        assert props["vintage"] is None
        assert props["as_of"] is None
        assert props["license_name"] is None
        assert props["attribution"] is None
