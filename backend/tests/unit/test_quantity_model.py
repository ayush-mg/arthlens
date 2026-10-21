"""
Unit tests for the immutable Quantity domain model.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 4.1, 5.1).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).
"""

from dataclasses import FrozenInstanceError
import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity


class TestQuantityDomainModel:
    """Validate 15-field Quantity dataclass invariants, immutability, and validation."""

    def test_quantity_valid_creation(self):
        """A valid Quantity record can be instantiated with all 15 handbook fields."""
        q = Quantity(
            id="q_valid_001",
            definition_key="population.total",
            value=1250000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_v1", "table_1"),),
            method_id="census_ingest",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        assert q.id == "q_valid_001"
        assert q.value == 1250000.0
        assert q.unit == "persons"
        assert q.kind == Kind.OBSERVED
        assert q.evidence_floor == 4
        assert q.resolution == 2

    def test_quantity_is_frozen_immutable(self):
        """Quantity instances reject attribute reassignment once constructed."""
        q = Quantity(
            id="q_frozen_001",
            definition_key="population.total",
            value=100.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            q.value = 200.0
        with pytest.raises((FrozenInstanceError, AttributeError)):
            q.kind = Kind.CALCULATED

    def test_quantity_rejects_invalid_evidence_floor(self):
        """Evidence floor must be an integer between 1 and 4 (Handbook 4.2)."""
        with pytest.raises(ValueError, match="evidence_floor"):
            Quantity(
                id="q_invalid_floor",
                definition_key="test.key",
                value=1.0,
                unit="dimensionless",
                kind=Kind.SCENARIO,
                evidence_floor=5,  # Invalid: must be 1..4
                geo_unit_id="nation",
                resolution=0,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="manual",
                model_version="1.0",
                parent_ids=(),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )

    def test_quantity_rejects_invalid_resolution(self):
        """Resolution must be an integer between 0 and 5 (Handbook 4.3)."""
        with pytest.raises(ValueError, match="resolution"):
            Quantity(
                id="q_invalid_res",
                definition_key="test.key",
                value=1.0,
                unit="dimensionless",
                kind=Kind.SCENARIO,
                evidence_floor=1,
                geo_unit_id="nation",
                resolution=6,  # Invalid: must be 0..5
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="manual",
                model_version="1.0",
                parent_ids=(),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )

    def test_quantity_rejects_observed_with_parents(self):
        """An OBSERVED quantity cannot have parent quantities (Handbook 4.1, 4.2)."""
        with pytest.raises(ValueError, match="OBSERVED"):
            Quantity(
                id="q_invalid_obs",
                definition_key="test.key",
                value=1.0,
                unit="dimensionless",
                kind=Kind.OBSERVED,
                evidence_floor=4,
                geo_unit_id="nation",
                resolution=0,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="manual",
                model_version="1.0",
                parent_ids=("parent_001",),  # Invalid for OBSERVED
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )

    def test_quantity_rejects_empty_id(self):
        """Quantity id and definition_key cannot be empty strings."""
        with pytest.raises(ValueError, match="id"):
            Quantity(
                id="",
                definition_key="test.key",
                value=1.0,
                unit="dimensionless",
                kind=Kind.USER_ASSUMED,
                evidence_floor=3,
                geo_unit_id="nation",
                resolution=0,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="manual",
                model_version="1.0",
                parent_ids=(),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )
