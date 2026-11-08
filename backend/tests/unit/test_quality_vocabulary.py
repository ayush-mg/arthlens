"""
Unit Tests for Quality Vocabulary, Design Tokens, and Precedence (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 7.5 Step 10, Part 10.2).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).
"""

import pytest
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.evaluator import DataQualityEvaluator
from backend.arthlens.quality.vocabulary import (
    ATLAS_SHADING_TOKENS,
    CalculationSuitability,
    QualityStatus,
    resolve_primary_status,
)


class TestQualityVocabularyAndPrecedence:
    """Tests for the six quality statuses and deterministic precedence."""

    def test_vocabulary_contains_exact_six_handbook_statuses(self):
        """Quality vocabulary must contain CURRENT, INCOMPLETE, STALE, ESTIMATED, UNAVAILABLE, CONTRADICTED."""
        expected = {"CURRENT", "INCOMPLETE", "STALE", "ESTIMATED", "UNAVAILABLE", "CONTRADICTED"}
        actual = {s.value for s in QualityStatus}
        assert actual == expected

    def test_shading_tokens_exist_for_all_six_statuses(self):
        """Every quality status must have a stable, non-null design token and hex color."""
        for status in QualityStatus:
            token = ATLAS_SHADING_TOKENS[status]
            assert token.status == status
            assert token.hex_color.startswith("#")
            assert len(token.hex_color) == 7
            assert 0.0 < token.fill_opacity <= 1.0
            assert token.color_token.startswith("atlas-quality-")
            assert token.label

    def test_exact_design_tokens(self):
        """Assert exact colors for the presentation states."""
        assert ATLAS_SHADING_TOKENS[QualityStatus.CURRENT].hex_color == "#22C55E"
        assert ATLAS_SHADING_TOKENS[QualityStatus.INCOMPLETE].hex_color == "#EAB308"
        assert ATLAS_SHADING_TOKENS[QualityStatus.STALE].hex_color == "#F97316"
        assert ATLAS_SHADING_TOKENS[QualityStatus.ESTIMATED].hex_color == "#3B82F6"
        assert ATLAS_SHADING_TOKENS[QualityStatus.UNAVAILABLE].hex_color == "#94A3B8"
        assert ATLAS_SHADING_TOKENS[QualityStatus.CONTRADICTED].hex_color == "#DC2626"

    def test_precedence_order_rules(self):
        """
        Deterministic precedence order:
        UNAVAILABLE (1) > CONTRADICTED (2) > INCOMPLETE (3) > STALE (4) > ESTIMATED (5) > CURRENT (6).
        """
        # UNAVAILABLE beats everything
        assert resolve_primary_status([QualityStatus.CURRENT, QualityStatus.UNAVAILABLE]) == QualityStatus.UNAVAILABLE
        assert resolve_primary_status([QualityStatus.STALE, QualityStatus.UNAVAILABLE]) == QualityStatus.UNAVAILABLE
        assert resolve_primary_status([QualityStatus.ESTIMATED, QualityStatus.UNAVAILABLE]) == QualityStatus.UNAVAILABLE
        assert resolve_primary_status([QualityStatus.INCOMPLETE, QualityStatus.UNAVAILABLE]) == QualityStatus.UNAVAILABLE
        assert resolve_primary_status([QualityStatus.CONTRADICTED, QualityStatus.UNAVAILABLE]) == QualityStatus.UNAVAILABLE

        # CONTRADICTED beats INCOMPLETE, STALE, ESTIMATED, CURRENT
        assert resolve_primary_status([QualityStatus.CURRENT, QualityStatus.CONTRADICTED]) == QualityStatus.CONTRADICTED
        assert resolve_primary_status([QualityStatus.STALE, QualityStatus.CONTRADICTED]) == QualityStatus.CONTRADICTED
        assert resolve_primary_status([QualityStatus.INCOMPLETE, QualityStatus.CONTRADICTED]) == QualityStatus.CONTRADICTED
        assert resolve_primary_status([QualityStatus.ESTIMATED, QualityStatus.CONTRADICTED]) == QualityStatus.CONTRADICTED

        # INCOMPLETE beats STALE, ESTIMATED, CURRENT
        assert resolve_primary_status([QualityStatus.CURRENT, QualityStatus.INCOMPLETE]) == QualityStatus.INCOMPLETE
        assert resolve_primary_status([QualityStatus.STALE, QualityStatus.INCOMPLETE]) == QualityStatus.INCOMPLETE
        assert resolve_primary_status([QualityStatus.ESTIMATED, QualityStatus.INCOMPLETE]) == QualityStatus.INCOMPLETE

        # STALE beats ESTIMATED, CURRENT
        assert resolve_primary_status([QualityStatus.CURRENT, QualityStatus.STALE]) == QualityStatus.STALE
        assert resolve_primary_status([QualityStatus.ESTIMATED, QualityStatus.STALE]) == QualityStatus.STALE

        # ESTIMATED beats CURRENT
        assert resolve_primary_status([QualityStatus.CURRENT, QualityStatus.ESTIMATED]) == QualityStatus.ESTIMATED

        # Pure CURRENT
        assert resolve_primary_status([QualityStatus.CURRENT]) == QualityStatus.CURRENT

        # Empty returns UNAVAILABLE
        assert resolve_primary_status([]) == QualityStatus.UNAVAILABLE

    def test_string_case_insensitivity_in_resolve_primary_status(self):
        """resolve_primary_status accepts uppercase, lowercase, and mixed strings."""
        assert resolve_primary_status(["current", "stale"]) == QualityStatus.STALE
        assert resolve_primary_status(["unavailable", "current"]) == QualityStatus.UNAVAILABLE


class TestClassificationEvaluatorScenarios:
    """Tests evaluating each of the five classification scenarios."""

    @pytest.fixture
    def evaluator(self):
        return DataQualityEvaluator(evaluation_date="2026-11-06")

    def test_current_complete_evidence(self, evaluator):
        """Fresh, empirical, complete observation with approved policy is classified as CURRENT."""
        fresh_q = Quantity(
            id="q_fresh",
            definition_key="population.recent_survey",
            value=142.0,
            unit="dimensionless",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",  # ~36 days old, within DS-05 3650-day threshold
            source_refs=("DS-05",),
        )
        res = evaluator.evaluate_quantity(
            fresh_q, "population.recent_survey", "in:district:120", source_id="DS-05"
        )
        assert res.primary_status == QualityStatus.CURRENT
        assert res.is_stale is False
        assert res.shading.hex_color == "#22C55E"
        assert res.suitability == CalculationSuitability.SUITABLE_CURRENT

    def test_unconfigured_policy_evidence_never_labeled_current(self, evaluator):
        """
        Evidence from a source lacking an approved freshness policy (e.g. DS-04, DS-08, DS-09)
        must NEVER be labeled CURRENT solely because no threshold exists.
        """
        unverified_q = Quantity(
            id="q_unverified",
            definition_key="pois.commercial",
            value=142.0,
            unit="dimensionless",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
            source_refs=("DS-04",),  # DS-04 lacks approved threshold
        )
        res = evaluator.evaluate_quantity(
            unverified_q, "pois.commercial", "in:district:120", source_id="DS-04"
        )
        assert res.primary_status != QualityStatus.CURRENT
        assert res.primary_status == QualityStatus.INCOMPLETE
        assert any("lacks an approved freshness policy" in i.reason for i in res.issues)

    def test_source_version_reference_is_not_treated_as_a_source_id(self, evaluator):
        quantity = Quantity(
            id="q_unresolved_version",
            definition_key="population.total",
            value=1.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2011-03-01",
            source_refs=(("registered-version-id", "table:row:1", "2011-04-01"),),
        )

        result = evaluator.evaluate_quantity(quantity, "population.total", "in:district:120")

        assert result.source_id is None
        assert result.is_stale is False
        assert result.primary_status == QualityStatus.INCOMPLETE
        assert any(issue.dimension == "temporal_freshness" for issue in result.issues)

    def test_incomplete_geographic_coverage(self, evaluator):
        """Observation with missing sub-units is classified as INCOMPLETE."""
        q = Quantity(
            id="q_district",
            definition_key="population.total",
            value=5954391.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
            source_refs=("DS-05",),
        )
        # Expected 8 tehsils, but only 5 provided
        expected_tehsils = ["in:subdistrict:120:888", "in:subdistrict:120:889", "in:subdistrict:120:890", "in:subdistrict:120:891", "in:subdistrict:120:892", "in:subdistrict:120:893", "in:subdistrict:120:894", "in:subdistrict:120:895"]
        actual_tehsils = ["in:subdistrict:120:888", "in:subdistrict:120:889", "in:subdistrict:120:890"]

        res = evaluator.evaluate_quantity(
            q,
            "population.total",
            "in:district:120",
            source_id="DS-05",
            expected_subunits=expected_tehsils,
            actual_subunits=actual_tehsils,
        )
        assert res.primary_status == QualityStatus.INCOMPLETE
        assert res.shading.hex_color == "#EAB308"
        assert res.suitability == CalculationSuitability.CAUTION_PARTIAL
        assert any("sub-unit" in i.reason.lower() for i in res.issues)

    def test_stale_evidence(self, evaluator):
        """Observation exceeding source maximum age is classified as STALE."""
        stale_q = Quantity(
            id="q_census",
            definition_key="population.total",
            value=5954391.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2011-03-01",  # 2011 Census is strictly stale in 2026
            source_refs=("DS-05",),
            quality_flags=frozenset({"STALE"}),
        )
        res = evaluator.evaluate_quantity(
            stale_q, "population.total", "in:district:120", source_id="DS-05"
        )
        assert res.primary_status == QualityStatus.STALE
        assert res.is_stale is True
        assert res.shading.hex_color == "#F97316"
        assert res.suitability == CalculationSuitability.SUITABLE_HISTORICAL_ONLY

    def test_estimated_evidence(self, evaluator):
        """Modelled or synthetic quantity is classified as ESTIMATED."""
        est_q = Quantity(
            id="q_est",
            definition_key="demand.monthly",
            value=85000.0,
            unit="INR/month",
            kind=Kind.ESTIMATED,
            evidence_floor=2,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
        )
        res = evaluator.evaluate_quantity(est_q, "demand.monthly", "in:district:120")
        assert res.primary_status == QualityStatus.ESTIMATED
        assert res.shading.hex_color == "#3B82F6"
        assert res.suitability == CalculationSuitability.ESTIMATED_PROJECTION

    def test_unavailable_evidence_never_silent_zero(self, evaluator):
        """Missing quantity is UNAVAILABLE, never numeric zero."""
        res = evaluator.evaluate_quantity(None, "electricity.consumption", "in:district:120")
        assert res.primary_status == QualityStatus.UNAVAILABLE
        assert res.value is None  # Strictly None, never 0.0
        assert res.shading.hex_color == "#94A3B8"
        assert res.suitability == CalculationSuitability.UNSUITABLE_MISSING
        assert "never represented as numeric zero" in res.explanation.lower()

    def test_multiple_simultaneous_issues_preserves_all_explanations(self, evaluator):
        """
        When an observation is BOTH stale AND estimated:
        - Primary status is STALE (by precedence STALE > ESTIMATED).
        - Both issues are preserved in the issues list with full reasons.
        """
        stale_and_est = Quantity(
            id="q_both",
            definition_key="population.projected",
            value=6200000.0,
            unit="persons",
            kind=Kind.ESTIMATED,
            evidence_floor=2,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2011-03-01",
            source_refs=("DS-05",),
            quality_flags=frozenset({"STALE", "SYNTHETIC_DATA"}),
        )
        res = evaluator.evaluate_quantity(
            stale_and_est, "population.projected", "in:district:120", source_id="DS-05"
        )
        assert res.primary_status == QualityStatus.STALE  # STALE has precedence over ESTIMATED
        statuses_in_issues = {i.status for i in res.issues}
        assert QualityStatus.STALE in statuses_in_issues
        assert QualityStatus.ESTIMATED in statuses_in_issues
        assert len(res.issues) >= 2

    def test_contradicted_evidence(self, evaluator):
        """Observation with CONTRADICTED or DISPUTED quality flag receives CONTRADICTED status."""
        contradicted_q = Quantity(
            id="q_disputed",
            definition_key="population.total",
            value=6500000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
            source_refs=("DS-05",),
            quality_flags=frozenset({"CONTRADICTED"}),
        )
        res = evaluator.evaluate_quantity(contradicted_q, "population.total", "in:district:120")
        assert res.primary_status == QualityStatus.CONTRADICTED
        assert res.shading.hex_color == "#DC2626"
        assert res.suitability == CalculationSuitability.UNSUITABLE_CONTRADICTED
        assert any("contradiction" in i.reason.lower() for i in res.issues)
