"""
Unit Tests for AdminBoundariesAdapter Hardening (P2-2.2).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.5).
Phase: Phase 2 (P2-2.2 - Adapter Hardening & Geographic Reconciliation).
"""

import pytest
from backend.arthlens.data.adapters.admin_boundaries import AdminBoundariesAdapter
from backend.arthlens.data.models import RawRecord
from backend.arthlens.domain.enums import ResolutionTier


class TestAdminBoundariesAdapterHardening:
    """Test suite ensuring AdminBoundariesAdapter never falsely reconciles incomplete or invalid boundary records."""

    @pytest.fixture
    def adapter(self):
        return AdminBoundariesAdapter()

    def test_missing_lgd_code_rejected(self, adapter):
        """Missing lgd_code in properties must return resolved=False, never claim resolved=True."""
        feat = {
            "type": "Feature",
            "properties": {
                "DISTRICT": "Test District",
                "ST_NM": "Uttar Pradesh",
                # lgd_code missing
                "level": 2,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        }
        raw = RawRecord(record_id="boundary:missing_lgd", source_id=adapter.source_id, payload=feat)
        norm = adapter.normalize_record(raw)
        recon = adapter.reconcile_geography(norm)

        assert recon.resolved is False
        assert recon.geo_unit_id is None
        assert "Missing" in recon.notes or "invalid" in recon.notes.lower()

    def test_empty_string_lgd_code_rejected(self, adapter):
        """Empty string or whitespace lgd_code must return resolved=False."""
        feat = {
            "type": "Feature",
            "properties": {
                "DISTRICT": "Test District",
                "lgd_code": "   ",
                "level": 2,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        }
        raw = RawRecord(record_id="boundary:empty_lgd", source_id=adapter.source_id, payload=feat)
        norm = adapter.normalize_record(raw)
        recon = adapter.reconcile_geography(norm)

        assert recon.resolved is False
        assert recon.geo_unit_id is None

    def test_missing_or_unknown_level_rejected(self, adapter):
        """Missing or unrecognized level must return resolved=False, never default to District."""
        feat = {
            "type": "Feature",
            "properties": {
                "DISTRICT": "Test District",
                "lgd_code": "175",
                # level missing
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        }
        raw = RawRecord(record_id="boundary:no_level", source_id=adapter.source_id, payload=feat)
        norm = adapter.normalize_record(raw)
        recon = adapter.reconcile_geography(norm)

        assert recon.resolved is False
        assert "level" in recon.notes.lower()

        # Invalid level value
        feat["properties"]["level"] = 99
        raw2 = RawRecord(record_id="boundary:bad_level", source_id=adapter.source_id, payload=feat)
        norm2 = adapter.normalize_record(raw2)
        recon2 = adapter.reconcile_geography(norm2)
        assert recon2.resolved is False

    def test_subdistrict_missing_parent_rejected(self, adapter):
        """Sub-district boundary feature missing parent_lgd_code must return resolved=False."""
        feat = {
            "type": "Feature",
            "properties": {
                "SUBDISTRICT": "Akbarpur",
                "lgd_code": "845",
                # parent_lgd_code missing
                "level": 3,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        }
        raw = RawRecord(record_id="boundary:orphan_subdist", source_id=adapter.source_id, payload=feat)
        norm = adapter.normalize_record(raw)
        recon = adapter.reconcile_geography(norm)

        assert recon.resolved is False
        assert "parent" in recon.notes.lower()

    def test_valid_district_boundary_reconciled_with_canonical_namespace(self, adapter):
        """Valid district feature reconciles to canonical namespace in:district:{lgd_code}."""
        feat = {
            "type": "Feature",
            "properties": {
                "DISTRICT": "Prayagraj",
                "lgd_code": "120",
                "level": 2,
                "parent_lgd_code": "09",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[81.52, 24.78], [82.35, 24.78], [82.35, 25.79], [81.52, 25.79], [81.52, 24.78]]],
            },
        }
        raw = RawRecord(record_id="boundary:120", source_id=adapter.source_id, payload=feat)
        norm = adapter.normalize_record(raw)
        recon = adapter.reconcile_geography(norm)

        assert recon.resolved is True
        assert recon.geo_unit_id == "in:district:120"
        assert recon.resolution_tier == ResolutionTier.DISTRICT

    def test_valid_subdistrict_boundary_reconciled_with_canonical_namespace(self, adapter):
        """Valid sub-district feature reconciles to canonical namespace in:subdistrict:{parent}:{child}."""
        feat = {
            "type": "Feature",
            "properties": {
                "SUBDISTRICT": "Sadar",
                "lgd_code": "890",
                "parent_lgd_code": "120",
                "level": 3,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[81.80, 25.40], [81.90, 25.40], [81.90, 25.50], [81.80, 25.50], [81.80, 25.40]]],
            },
        }
        raw = RawRecord(record_id="boundary:890", source_id=adapter.source_id, payload=feat)
        norm = adapter.normalize_record(raw)
        recon = adapter.reconcile_geography(norm)

        assert recon.resolved is True
        assert recon.geo_unit_id == "in:subdistrict:120:890"
        assert recon.resolution_tier == ResolutionTier.SUBDISTRICT


class TestSourceBoundBoundaryVerification:
    """Verifies that GEOMETRY_VERIFIED strictly requires the approved DS-09 snapshot and rejects unapproved/forged data."""

    def test_exact_approved_snapshot_acceptance(self):
        """Approved snapshot with matching hash, provenance, and Prayagraj identifiers receives GEOMETRY_VERIFIED."""
        from backend.arthlens.data.adapters.admin_boundaries import (
            APPROVED_PILOT_SNAPSHOT_SHA256,
            determine_boundary_geometry_status,
        )
        from backend.arthlens.domain.geo import GeometryStatus

        status, reason = determine_boundary_geometry_status(
            content_hash=APPROVED_PILOT_SNAPSHOT_SHA256,
            collection_provenance={
                "source_id": "DS-09",
                "district_name_current": "Prayagraj",
                "census_code": 175,
                "lgd_code": "120",
            },
            geo_id="in:district:120",
            lgd_code="120",
            census_code="175",
            name="Prayagraj",
            vintage="Census 2011",
        )
        assert status == GeometryStatus.GEOMETRY_VERIFIED
        assert "Approved" in reason

    def test_modified_snapshot_hash_rejection(self):
        """Modified content hash must not receive GEOMETRY_VERIFIED even if properties claim Prayagraj."""
        from backend.arthlens.data.adapters.admin_boundaries import determine_boundary_geometry_status
        from backend.arthlens.domain.geo import GeometryStatus

        status, reason = determine_boundary_geometry_status(
            content_hash="bad_hash_1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            collection_provenance={
                "source_id": "DS-09",
                "district_name_current": "Prayagraj",
                "census_code": 175,
                "lgd_code": "120",
            },
            geo_id="in:district:120",
            lgd_code="120",
            census_code="175",
            name="Prayagraj",
            vintage="Census 2011",
        )
        assert status != GeometryStatus.GEOMETRY_VERIFIED
        assert status == GeometryStatus.GEOMETRY_HISTORICAL

    def test_forged_feature_level_geometry_verified_rejected(self):
        """A feature asserting geometry_status=GEOMETRY_VERIFIED on an unapproved snapshot must be rejected."""
        from backend.arthlens.data.adapters.admin_boundaries import determine_boundary_geometry_status
        from backend.arthlens.domain.geo import GeometryStatus

        status, _ = determine_boundary_geometry_status(
            content_hash="forged_hash_000000",
            collection_provenance=None,
            geo_id="in:district:187",  # Varanasi
            lgd_code="187",
            census_code="197",
            name="Varanasi",
            vintage="2024",
        )
        assert status != GeometryStatus.GEOMETRY_VERIFIED
        assert status == GeometryStatus.GEOMETRY_UNVALIDATED

    def test_missing_collection_level_provenance_rejected(self):
        """Payload without collection-level provenance cannot receive GEOMETRY_VERIFIED."""
        from backend.arthlens.data.adapters.admin_boundaries import (
            APPROVED_PILOT_SNAPSHOT_SHA256,
            determine_boundary_geometry_status,
        )
        from backend.arthlens.domain.geo import GeometryStatus

        status, _ = determine_boundary_geometry_status(
            content_hash=APPROVED_PILOT_SNAPSHOT_SHA256,
            collection_provenance=None,  # Missing provenance dictionary
            geo_id="in:district:120",
            lgd_code="120",
            census_code="175",
            name="Prayagraj",
            vintage="Census 2011",
        )
        assert status != GeometryStatus.GEOMETRY_VERIFIED
        assert status == GeometryStatus.GEOMETRY_HISTORICAL

    def test_wrong_geographic_identity_rejected(self):
        """Approved snapshot hash with wrong district identity (e.g. Varanasi or wrong Census code) is not verified."""
        from backend.arthlens.data.adapters.admin_boundaries import (
            APPROVED_PILOT_SNAPSHOT_SHA256,
            determine_boundary_geometry_status,
        )
        from backend.arthlens.domain.geo import GeometryStatus

        status, _ = determine_boundary_geometry_status(
            content_hash=APPROVED_PILOT_SNAPSHOT_SHA256,
            collection_provenance={"source_id": "DS-09"},
            geo_id="in:district:187",  # Varanasi
            lgd_code="187",
            census_code="197",
            name="Varanasi",
            vintage="Census 2011",
        )
        assert status != GeometryStatus.GEOMETRY_VERIFIED
        assert status == GeometryStatus.GEOMETRY_HISTORICAL

    def test_unapproved_geometry_without_supported_vintage_remains_unvalidated(self):
        """Unapproved snapshot without Census 2011 vintage remains GEOMETRY_UNVALIDATED."""
        from backend.arthlens.data.adapters.admin_boundaries import determine_boundary_geometry_status
        from backend.arthlens.domain.geo import GeometryStatus

        status, reason = determine_boundary_geometry_status(
            content_hash="unknown_hash",
            collection_provenance=None,
            geo_id="in:district:120",
            lgd_code="120",
            census_code="175",
            name="Prayagraj",
            vintage="2026-experimental",
        )
        assert status == GeometryStatus.GEOMETRY_UNVALIDATED
        assert "unapproved" in reason.lower()


class TestInMemoryGeoUnitRepositoryInvariants:
    """Verifies that InMemoryGeoUnitRepository enforces consistent domain invariants."""

    @staticmethod
    def _create_repo_with_district():
        from backend.arthlens.domain.enums import ResolutionTier
        from backend.arthlens.domain.geo import GeometryStatus, GeoUnit, NavigationStatus
        from backend.arthlens.infra.in_memory import InMemoryGeoUnitRepository

        repo = InMemoryGeoUnitRepository()
        nation = GeoUnit(
            id="in",
            parent_id=None,
            level=ResolutionTier.NATION,
            name="India",
            lgd_code="IN",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        repo.save_unit(nation)
        state = GeoUnit(
            id="in:state:09",
            parent_id="in",
            level=ResolutionTier.STATE,
            name="Uttar Pradesh",
            lgd_code="09",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        repo.save_unit(state)
        return repo

    def test_update_geometry_inconsistent_statuses_rejected(self):
        """Non-null geometry cannot be stored with GEOMETRY_MISSING; null geometry cannot be VERIFIED."""
        from backend.arthlens.domain.enums import ResolutionTier
        from backend.arthlens.domain.geo import GeometryStatus, GeoUnit, NavigationStatus

        repo = self._create_repo_with_district()
        unit = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        repo.save_unit(unit)

        valid_poly = {
            "type": "Polygon",
            "coordinates": [[[81.5, 24.8], [82.3, 24.8], [82.3, 25.7], [81.5, 25.5], [81.5, 24.8]]],
        }

        # Storing non-null geometry with GEOMETRY_MISSING must be rejected
        res1 = repo.update_geometry(
            unit_id="in:district:120",
            geometry=valid_poly,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        assert res1 is False

        # Storing null geometry with GEOMETRY_VERIFIED must be rejected
        res2 = repo.update_geometry(
            unit_id="in:district:120",
            geometry=None,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        )
        assert res2 is False

    def test_update_geometry_rejects_non_areal_geometry(self):
        """Point, LineString, and MultiPoint geometries must be rejected."""
        from backend.arthlens.domain.enums import ResolutionTier
        from backend.arthlens.domain.geo import GeometryStatus, GeoUnit, NavigationStatus

        repo = self._create_repo_with_district()
        unit = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        repo.save_unit(unit)

        point_geom = {"type": "Point", "coordinates": [81.8, 25.4]}
        res = repo.update_geometry(
            unit_id="in:district:120",
            geometry=point_geom,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        )
        assert res is False

    def test_update_geometry_preserves_stronger_existing_geometry(self):
        """A verified geometry must not be downgraded by a weaker candidate when preserve_existing=True."""
        from backend.arthlens.domain.enums import ResolutionTier
        from backend.arthlens.domain.geo import GeometryStatus, GeoUnit, NavigationStatus

        repo = self._create_repo_with_district()
        valid_poly = {
            "type": "Polygon",
            "coordinates": [[[81.5, 24.8], [82.3, 24.8], [82.3, 25.7], [81.5, 25.5], [81.5, 24.8]]],
        }
        unit = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
            geometry=valid_poly,
        )
        repo.save_unit(unit)

        # Attempt to overwrite with GEOMETRY_HISTORICAL (weaker rank)
        weaker_poly = {
            "type": "Polygon",
            "coordinates": [[[81.6, 24.9], [82.2, 24.9], [82.2, 25.6], [81.6, 25.4], [81.6, 24.9]]],
        }
        res = repo.update_geometry(
            unit_id="in:district:120",
            geometry=weaker_poly,
            geometry_status=GeometryStatus.GEOMETRY_HISTORICAL,
            preserve_existing=True,
        )
        assert res is False

        # Unit must retain its original verified geometry
        u = repo.get_unit("in:district:120")
        assert u.geometry_status == GeometryStatus.GEOMETRY_VERIFIED
        assert u.geometry == valid_poly

