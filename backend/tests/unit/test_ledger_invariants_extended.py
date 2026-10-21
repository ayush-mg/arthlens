"""
Extended unit tests for Epistemic Ledger invariants enforcement.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.2, 4.3, 4.4, 4.7).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).
"""

from datetime import date
import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.downscaling import DownscalingRegistry
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.propagation import propagate_quality_flags
from backend.arthlens.ledger.staleness import (
    apply_staleness_flag,
    is_source_stale,
    with_staleness_flag,
)


class TestLedgerInvariantsEnforcement:
    """Verify runtime enforcement of evidence floor and downscaling rules in Ledger."""

    def test_derived_cannot_strengthen_evidence_floor(self):
        """A derived quantity cannot declare a higher evidence floor than its weakest parent (Handbook 4.2)."""
        ledger = Ledger()
        parent_id = ledger.register(Quantity(
            id="p_est",
            definition_key="test.est",
            value=100.0,
            unit="INR",
            kind=Kind.ESTIMATED,
            evidence_floor=2,
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
        ))

        # Attempt to register child with floor=3 (> parent floor=2)
        with pytest.raises(ValueError, match="must equal min of parents"):
            ledger.register(Quantity(
                id="c_illegal_floor",
                definition_key="test.derived",
                value=200.0,
                unit="INR",
                kind=Kind.CALCULATED,
                evidence_floor=3,  # Illegal: parent is 2
                geo_unit_id="district_001",
                resolution=2,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="calc",
                model_version="1.0",
                parent_ids=(parent_id,),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            ))

    def test_derived_cannot_have_unnecessarily_lower_evidence_floor(self):
        """
        Check 1 (Handbook 4.2):
        evidence_floor(child) = min(evidence_floor(parent) for parent in parents).
        A derived quantity must not be registered with an unnecessarily lower floor.
        For example, if all parents have evidence_floor=4, a derived quantity must not
        be registered with evidence_floor=1 or 3.
        """
        ledger = Ledger()
        parent_id = ledger.register(Quantity(
            id="p_obs_floor4",
            definition_key="test.parent_floor4",
            value=500.0,
            unit="INR",
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
        ))

        # Attempt to register child with floor=1 (< min parent floor=4)
        with pytest.raises(ValueError, match="must equal min of parents"):
            ledger.register(Quantity(
                id="c_lower_floor_1",
                definition_key="test.derived.floor1",
                value=250.0,
                unit="INR",
                kind=Kind.CALCULATED,
                evidence_floor=1,  # Unnecessarily lower
                geo_unit_id="district_001",
                resolution=2,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="calc",
                model_version="1.0",
                parent_ids=(parent_id,),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            ))

        # Attempt to register child with floor=3 (< min parent floor=4)
        with pytest.raises(ValueError, match="must equal min of parents"):
            ledger.register(Quantity(
                id="c_lower_floor_3",
                definition_key="test.derived.floor3",
                value=250.0,
                unit="INR",
                kind=Kind.CALCULATED,
                evidence_floor=3,  # Unnecessarily lower
                geo_unit_id="district_001",
                resolution=2,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="calc",
                model_version="1.0",
                parent_ids=(parent_id,),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            ))

        # Registering with exact floor=4 succeeds
        valid_child_id = ledger.register(Quantity(
            id="c_exact_floor_4",
            definition_key="test.derived.floor4",
            value=250.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="calc",
            model_version="1.0",
            parent_ids=(parent_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))
        assert ledger.get(valid_child_id).evidence_floor == 4

    def test_resolution_refinement_without_downscaling_rejected(self):
        """A derived quantity cannot refine resolution without a registered downscaling method (Handbook 4.3)."""
        ledger = Ledger()
        parent_id = ledger.register(Quantity(
            id="p_dist",
            definition_key="test.dist",
            value=1000.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,  # DISTRICT
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        # Attempt to refine to resolution=3 (SUBDISTRICT) with unregistered/empty method
        with pytest.raises(ValueError, match="Resolution cannot refine"):
            ledger.register(Quantity(
                id="c_illegal_res",
                definition_key="test.subdist",
                value=500.0,
                unit="INR",
                kind=Kind.ESTIMATED,
                evidence_floor=2,
                geo_unit_id="subdistrict_001",
                resolution=3,  # Finer than parent (3 > 2)
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="unregistered_random_method",
                model_version="1.0",
                parent_ids=(parent_id,),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            ))

    def test_downscaled_refinement_must_be_estimated_kind(self):
        """Downscaling outputs must have kind=ESTIMATED (Handbook 4.3)."""
        ledger = Ledger()
        parent_id = ledger.register(Quantity(
            id="p_dist_2",
            definition_key="test.dist2",
            value=1000.0,
            unit="INR",
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
        ))

        # Downscaling method is popweight_v1 (registered), but kind is CALCULATED instead of ESTIMATED
        with pytest.raises(ValueError, match="Downscaled quantity must have kind ESTIMATED"):
            ledger.register(Quantity(
                id="c_illegal_kind",
                definition_key="test.subdist2",
                value=500.0,
                unit="INR",
                kind=Kind.CALCULATED,  # Illegal: must be ESTIMATED
                evidence_floor=2,
                geo_unit_id="subdistrict_001",
                resolution=3,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="popweight_v1",
                model_version="1.0",
                parent_ids=(parent_id,),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            ))

    def test_downscaled_refinement_floor_cap_at_two(self):
        """Downscaled outputs must have evidence_floor at most 2 (Handbook 4.3)."""
        ledger = Ledger()
        parent_id = ledger.register(Quantity(
            id="p_dist_3",
            definition_key="test.dist3",
            value=1000.0,
            unit="INR",
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
        ))

        # Downscaled with popweight_v1, kind=ESTIMATED, but evidence_floor=3 (> 2)
        with pytest.raises(ValueError, match="evidence_floor at most 2"):
            ledger.register(Quantity(
                id="c_illegal_floor_2",
                definition_key="test.subdist3",
                value=500.0,
                unit="INR",
                kind=Kind.ESTIMATED,
                evidence_floor=3,  # Illegal: must be <= 2
                geo_unit_id="subdistrict_001",
                resolution=3,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="popweight_v1",
                model_version="1.0",
                parent_ids=(parent_id,),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            ))

    def test_valid_downscaling_registration_succeeds(self):
        """A valid downscaled quantity with registered method, ESTIMATED kind, and floor<=2 registers successfully."""
        ledger = Ledger()
        parent_id = ledger.register(Quantity(
            id="p_dist_valid",
            definition_key="test.dist.valid",
            value=1000.0,
            unit="INR",
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
        ))

        child_id = ledger.register(Quantity(
            id="c_valid_downscale",
            definition_key="test.subdist.valid",
            value=500.0,
            unit="INR",
            kind=Kind.ESTIMATED,
            evidence_floor=2,  # Valid (min(4, 2) == 2)
            geo_unit_id="subdistrict_001",
            resolution=3,  # Valid refinement via popweight_v1
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="popweight_v1",
            model_version="1.0",
            parent_ids=(parent_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))
        assert child_id == "c_valid_downscale"
        retrieved = ledger.get(child_id)
        assert retrieved.resolution == 3
        assert retrieved.kind == Kind.ESTIMATED
        assert retrieved.evidence_floor == 2


class TestStalenessDetectionAndPropagation:
    """
    Check 2 (Handbook 4.4, 4.7):
    'Each source has a configured maximum age. Beyond it the quantity
    gets the STALE flag; derived quantities inherit STALE.'
    """

    def test_source_within_allowed_age_not_stale(self):
        """A quantity within its configured max_age_days is not stale and does not receive STALE."""
        ref_date = date(2026, 10, 20)
        # as_of is 2026-06-01 (141 days old)
        as_of = "2026-06-01"
        max_age_days = 365  # Configured source max age: 1 year

        stale = is_source_stale(as_of, max_age_days=max_age_days, reference_date=ref_date)
        assert stale is False

        q = Quantity(
            id="q_fresh_source",
            definition_key="source.fresh_metric",
            value=100.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of=as_of,
            uncertainty="EXACT",
            source_refs=(),
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        q_evaluated = with_staleness_flag(q, max_age_days=max_age_days, reference_date=ref_date)
        assert "STALE" not in q_evaluated.quality_flags
        assert q_evaluated.quality_flags == frozenset()

    def test_source_exceeding_maximum_age_receives_stale_flag(self):
        """A quantity exceeding its configured max_age_days gets the STALE quality flag assigned."""
        ref_date = date(2026, 10, 20)
        # as_of is 2025-01-01 (657 days old)
        as_of = "2025-01-01"
        max_age_days = 180  # Configured source max age: 180 days

        stale = is_source_stale(as_of, max_age_days=max_age_days, reference_date=ref_date)
        assert stale is True

        q = Quantity(
            id="q_stale_source",
            definition_key="source.stale_metric",
            value=50.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of=as_of,
            uncertainty="EXACT",
            source_refs=(),
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        q_stale = with_staleness_flag(q, max_age_days=max_age_days, reference_date=ref_date)
        assert "STALE" in q_stale.quality_flags
        assert q_stale.id == "q_stale_source"

    def test_stale_flag_propagates_to_derived_quantity(self):
        """
        When a parent quantity has the STALE flag, derived quantities inherit STALE.
        The ledger enforces that derived quantities register with inherited parent flags.
        """
        ledger = Ledger()
        ref_date = date(2026, 10, 20)

        # Parent source exceeds max age (as_of 2024-01-01 > 365 days)
        parent_raw = Quantity(
            id="q_stale_parent",
            definition_key="census.population",
            value=100000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2024-01-01",
            uncertainty="EXACT",
            source_refs=(),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        parent_stale = with_staleness_flag(parent_raw, max_age_days=365, reference_date=ref_date)
        assert "STALE" in parent_stale.quality_flags
        parent_id = ledger.register(parent_stale)

        # Child inherits flags via propagate_quality_flags
        child_flags = propagate_quality_flags([parent_stale.quality_flags])
        assert "STALE" in child_flags

        child = Quantity(
            id="q_derived_child",
            definition_key="census.population_adjusted",
            value=105000.0,
            unit="persons",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="calc",
            model_version="1.0",
            parent_ids=(parent_id,),
            quality_flags=child_flags,
            license_meta="GODL-India",
        )
        child_id = ledger.register(child)
        assert "STALE" in ledger.get(child_id).quality_flags

        # If a derived quantity attempts to drop the parent's STALE flag, ledger rejects it
        child_without_stale = Quantity(
            id="q_derived_missing_stale",
            definition_key="census.population_adjusted_drop",
            value=105000.0,
            unit="persons",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="calc",
            model_version="1.0",
            parent_ids=(parent_id,),
            quality_flags=frozenset(),  # Missing STALE
            license_meta="GODL-India",
        )
        with pytest.raises(ValueError, match="Derived quantity must inherit parent quality flags"):
            ledger.register(child_without_stale)
