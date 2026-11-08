"""
Unit tests for FIX 5: Handbook V5 Contradiction Detection.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.4, 4.5, Part 7.4).
Phase: Phase 2 Final Integration.

Verifies:
1. Matching definition_key + canonical geo_unit_id + compatible temporal period.
2. Contradiction detected when values disagree beyond registered metric tolerance.
3. Both conflicting quantities remain visible and are marked DISPUTED.
4. Different temporal periods (e.g. 2011 vs 2026) are not contradicted.
5. Different geographic units are not contradicted.
6. Overlapping uncertainty intervals are not contradicted.
7. Unconfigured metric policy falls back to zero-tolerance point comparison without inventing arbitrary thresholds.
"""


from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.contradiction import (
    ContradictionRegistry,
    MetricTolerancePolicy,
    detect_contradictions,
)


def test_matching_observations_beyond_tolerance_marked_disputed():
    """
    Two sources reporting different population totals for Prayagraj in 2011
    disagree beyond 1% registered tolerance -> contradiction detected!
    """
    q1 = Quantity(
        id="q_census_1",
        definition_key="population.total",
        value=5954391.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2011-03-01",
        source_refs=("DS-05:v1",),
    )
    # Municipal estimate for the same district and year: 6,500,000 (>9% higher, exceeds 1% tolerance)
    q2 = Quantity(
        id="q_municipal_2",
        definition_key="population.total",
        value=6500000.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2011-03-01",
        source_refs=("DS-LOCAL:v1",),
    )

    contradicted_ids, records = detect_contradictions([q1, q2])
    assert "q_census_1" in contradicted_ids
    assert "q_municipal_2" in contradicted_ids
    assert len(records) == 1
    assert records[0].definition_key == "population.total"
    assert records[0].geo_unit_id == "in:district:120"


def test_different_temporal_periods_are_not_contradicted():
    """
    Census 2011 (5.95M) and Model 2026 (7.2M) refer to different observation periods;
    they are NOT a contradiction.
    """
    q_2011 = Quantity(
        id="q_2011",
        definition_key="population.total",
        value=5954391.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2011-03-01",
        source_refs=("DS-05",),
    )
    q_2026 = Quantity(
        id="q_2026",
        definition_key="population.total",
        value=7200000.0,
        unit="persons",
        kind=Kind.ESTIMATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-10-01",
        source_refs=("DS-PROJECTION",),
    )

    contradicted_ids, records = detect_contradictions([q_2011, q_2026])
    assert len(contradicted_ids) == 0
    assert len(records) == 0


def test_different_geographic_units_are_not_contradicted():
    """Observations for Prayagraj (120) and Varanasi (187) do not contradict."""
    q_prayagraj = Quantity(
        id="q_prayagraj",
        definition_key="population.total",
        value=5954391.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2011-03-01",
        source_refs=("DS-05",),
    )
    q_varanasi = Quantity(
        id="q_varanasi",
        definition_key="population.total",
        value=3676841.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:187",
        resolution=2,
        as_of="2011-03-01",
        source_refs=("DS-05",),
    )

    contradicted_ids, records = detect_contradictions([q_prayagraj, q_varanasi])
    assert len(contradicted_ids) == 0


def test_overlapping_uncertainty_intervals_are_not_contradicted():
    """
    Two quantities with uncertainty intervals that overlap are compatible,
    even if their point estimates differ slightly.
    """
    q_int1 = Quantity(
        id="q_int1",
        definition_key="demand.monthly",
        value=85000.0,
        unit="INR/month",
        kind=Kind.ESTIMATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-10-01",
        uncertainty=("INTERVAL", 80000.0, 90000.0),
        source_refs=("MODEL_GRAVITY_V1",),
    )
    q_int2 = Quantity(
        id="q_int2",
        definition_key="demand.monthly",
        value=88000.0,
        unit="INR/month",
        kind=Kind.ESTIMATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-10-01",
        uncertainty=("INTERVAL", 85000.0, 95000.0),  # Overlaps [85000, 90000]
        source_refs=("MODEL_SURVEY_V1",),
    )

    contradicted_ids, records = detect_contradictions([q_int1, q_int2])
    assert len(contradicted_ids) == 0


def test_disjoint_uncertainty_intervals_are_contradicted():
    """Disjoint uncertainty intervals [80k, 85k] and [90k, 95k] strictly contradict."""
    q_disjoint1 = Quantity(
        id="q_dj1",
        definition_key="demand.monthly",
        value=82000.0,
        unit="INR/month",
        kind=Kind.ESTIMATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-10-01",
        uncertainty=("INTERVAL", 80000.0, 85000.0),
        source_refs=("SOURCE_A",),
    )
    q_disjoint2 = Quantity(
        id="q_dj2",
        definition_key="demand.monthly",
        value=92000.0,
        unit="INR/month",
        kind=Kind.ESTIMATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-10-01",
        uncertainty=("INTERVAL", 90000.0, 95000.0),
        source_refs=("SOURCE_B",),
    )

    contradicted_ids, records = detect_contradictions([q_disjoint1, q_disjoint2])
    assert "q_dj1" in contradicted_ids
    assert "q_dj2" in contradicted_ids
    assert len(records) == 1


def test_tolerance_is_used_only_after_explicit_registration():
    q1 = Quantity(
        "q_tolerance_1",
        "test.metric",
        100.0,
        "dimensionless",
        Kind.OBSERVED,
        4,
        "in:district:120",
        2,
        "2026-01-01",
        source_refs=(("SRC:1", "row:1", "2026-01-01"),),
    )
    q2 = Quantity(
        "q_tolerance_2",
        "test.metric",
        101.0,
        "dimensionless",
        Kind.OBSERVED,
        4,
        "in:district:120",
        2,
        "2026-01-01",
        source_refs=(("SRC:2", "row:1", "2026-01-01"),),
    )
    ContradictionRegistry.reset_defaults()
    assert detect_contradictions([q1, q2])[0] == {"q_tolerance_1", "q_tolerance_2"}
    ContradictionRegistry.register_policy(
        MetricTolerancePolicy("test.metric", relative_tolerance=0.02, description="test policy")
    )
    assert detect_contradictions([q1, q2])[0] == set()
    ContradictionRegistry.reset_defaults()
