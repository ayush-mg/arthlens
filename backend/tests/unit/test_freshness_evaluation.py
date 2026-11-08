"""
Unit Tests for Freshness Policies, Injected Clocks, and Census 2011 Staleness (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.4, Part 7.1, 7.5 Step 10).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).
"""

from datetime import date

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.freshness import (
    FreshnessRegistry,
    evaluate_staleness,
)


class TestFreshnessEvaluation:
    """Tests evaluating temporal freshness under injected clocks and policy boundaries."""

    def test_ten_year_boundary_exact_threshold(self):
        """
        Verify exact date arithmetic for as_of = 2011-03-01 and max_age_days = 3650:
        - Exactly 3650 elapsed days corresponds to 2021-02-26 (due to leap years 2012, 2016, 2020) -> NOT stale.
        - Exactly 3651 elapsed days corresponds to 2021-02-27 -> strictly STALE.
        """
        base_as_of = date(2011, 3, 1)

        # Day 3650: exactly 2021-02-26 -> NOT stale
        eval_exact = date(2021, 2, 26)
        assert (eval_exact - base_as_of).days == 3650
        res_exact = evaluate_staleness(
            as_of=base_as_of,
            source_id="DS-05",  # max_age_days = 3650
            evaluation_date=eval_exact,
        )
        assert res_exact.is_stale is False
        assert res_exact.elapsed_days == 3650

        # Day 3651: exactly 2021-02-27 -> strictly STALE
        eval_beyond = date(2021, 2, 27)
        assert (eval_beyond - base_as_of).days == 3651
        res_beyond = evaluate_staleness(
            as_of=base_as_of,
            source_id="DS-05",
            evaluation_date=eval_beyond,
        )
        assert res_beyond.is_stale is True
        assert res_beyond.elapsed_days == 3651
        assert "exceeds maximum threshold" in res_beyond.explanation.lower()

    def test_census_2011_evaluated_on_6_november_2026(self):
        """
        Census 2011 (as_of 2011-03-01) evaluated on 6 November 2026 is strictly STALE (>15 years old).
        """
        eval_date = date(2026, 11, 6)
        res = evaluate_staleness(
            as_of="2011-03-01",
            source_id="DS-05",
            evaluation_date=eval_date,
        )
        assert res.is_stale is True
        assert res.elapsed_days > 5700
        assert res.max_age_days == 3650
        assert "ten-year staleness rule" in res.explanation.lower()
        assert "must never represent current population" in res.explanation.lower()

    def test_recent_download_never_makes_historical_observation_current(self):
        """
        Critical Invariant:
        Retrieving or downloading Census 2011 in November 2026 does NOT make it fresh or current.
        Staleness depends strictly on as_of observation date, not retrieval_date.
        """
        res = evaluate_staleness(
            as_of="2011-03-01",
            source_id="DS-05",
            retrieval_date="2026-11-06",  # Retrieved today!
            publication_date="2013-04-30",
            evaluation_date="2026-11-06",
        )
        assert res.is_stale is True
        assert res.retrieval_date == date(2026, 11, 6)
        assert res.as_of_date == date(2011, 3, 1)
        assert res.elapsed_days > 5700

    def test_missing_observation_date_fails_safely(self):
        """Missing as_of observation date reports has_policy=False and explanation."""
        res = evaluate_staleness(
            as_of=None,
            source_id="DS-05",
            evaluation_date="2026-11-06",
        )
        assert res.is_stale is False
        assert res.as_of_date is None
        assert "missing" in res.explanation.lower()

    def test_unknown_freshness_policy_not_guessed(self):
        """
        Sources lacking an approved policy must not receive an invented threshold.
        Freshness is reported as unverified (has_policy=False).
        """
        res = evaluate_staleness(
            as_of="2024-01-01",
            source_id="UNKNOWN_CUSTOM_SOURCE_XYZ",
            evaluation_date="2026-11-06",
        )
        assert res.is_stale is False
        assert res.has_policy is False
        assert res.max_age_days is None
        assert "lacks an approved freshness policy" in res.explanation

    def test_unapproved_sources_marked_unconfigured(self):
        """
        DS-04 (180 days), DS-08 (365 days), and DS-09 (1825 days) lack approved thresholds
        in their authoritative registers and are strictly unconfigured.
        """
        for unapproved_src in ["DS-04", "DS-08", "DS-09"]:
            assert FreshnessRegistry.get_policy(unapproved_src) is None
            eval_res = evaluate_staleness(
                as_of="2026-01-01",
                source_id=unapproved_src,
                evaluation_date="2026-11-06",
            )
            assert eval_res.has_policy is False
            assert "lacks an approved freshness policy" in eval_res.explanation

    def test_deterministic_injected_evaluation_date(self):
        """Staleness evaluation is deterministic and repeatable when evaluation_date is injected."""
        as_of = "2024-01-01"

        # Evaluated at 100 days with custom_max_age_days=180 (fresh)
        eval_100 = date(2024, 4, 10)
        assert evaluate_staleness(as_of, custom_max_age_days=180, evaluation_date=eval_100).is_stale is False

        # Evaluated at 250 days with custom_max_age_days=180 (stale)
        eval_250 = date(2024, 9, 7)
        assert evaluate_staleness(as_of, custom_max_age_days=180, evaluation_date=eval_250).is_stale is True

    def test_historical_lgd_crosswalk_vintage_freshness_unverified(self):
        """
        Preserved LGD crosswalk snapshot from third-party mirror has vintage March 2022 (2022-03-11).
        It must NOT be classified as CURRENT merely because LGD is an official government directory.
        Because no approved threshold exists, its freshness remains unverified (has_policy=False)
        and it cannot be automatically labeled CURRENT.
        """
        lgd_src = "DS-05-LGD"
        assert FreshnessRegistry.get_policy(lgd_src) is None

        # Evaluated on 6 November 2026
        res = evaluate_staleness(
            as_of="2022-03-11",  # Upstream source vintage
            source_id=lgd_src,
            evaluation_date="2026-11-06",
            publication_date="2022-03-11",
            retrieval_date="2026-11-06",
        )
        assert res.has_policy is False
        assert res.is_stale is False
        assert res.as_of_date == date(2022, 3, 11)
        assert res.publication_date == date(2022, 3, 11)
        assert res.retrieval_date == date(2026, 11, 6)
        assert "lacks an approved freshness policy" in res.explanation

        # Verify evaluator behavior: NEVER classified as CURRENT
        from backend.arthlens.quality.evaluator import DataQualityEvaluator
        from backend.arthlens.quality.vocabulary import QualityStatus

        evaluator = DataQualityEvaluator(evaluation_date="2026-11-06")

        # 1. Historical LGD administrative crosswalk evidence
        q_lgd = Quantity(
            id="q_lgd",
            definition_key="admin.lgd_subdistrict_code",
            value=890.0,
            unit="dimensionless",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2022-03-11",
            source_refs=("DS-05-LGD",),
        )
        lgd_assessment = evaluator.evaluate_quantity(q_lgd, "admin.lgd_subdistrict_code", "in:district:120")
        assert lgd_assessment.primary_status != QualityStatus.CURRENT
        assert lgd_assessment.primary_status == QualityStatus.INCOMPLETE
        assert any("lacks an approved freshness policy" in i.reason for i in lgd_assessment.issues)

        # 2. Census 2011 demographic count (separate policy: strictly STALE under 10-year rule)
        q_census = Quantity(
            id="q_census",
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
        census_assessment = evaluator.evaluate_quantity(
            q_census, "population.total", "in:district:120", source_id="DS-05"
        )
        assert census_assessment.primary_status == QualityStatus.STALE
        assert census_assessment.is_stale is True
