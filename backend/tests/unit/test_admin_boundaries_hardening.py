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

