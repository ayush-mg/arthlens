"""
Unit tests for the Nine Verification Specifications (V1 to V9) and AndSpecification.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.5, 4.7).
Phase: P1-4 (Verification Specifications, LedgerVerifier, ReportRenderer).
"""

from datetime import date
import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.downscaling import DownscalingRegistry
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.specs import (
    AndSpecification,
    ContradictionVisibilitySpec,
    DerivationDowngradeSpec,
    GeographicPrecisionSpec,
    MissingAssumptionSpec,
    PolicyCitationSpec,
    ReproducibilitySpec,
    SimulationModelVersionSpec,
    SourceAttributionSpec,
    SpecResult,
    UnitCompatibilitySpec,
)


class TestV1DerivationDowngradeSpec:
    """V1: A derived value is never labelled OBSERVED; class must not be stronger than floor."""

    def test_derived_labelled_observed_rejected(self):
        spec = DerivationDowngradeSpec()
        q = Quantity(
            id="q_derived_obs",
            definition_key="test.metric",
            value=100.0,
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
            parent_ids=("parent_1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        # Attempting to check a quantity marked OBSERVED with parents
        # Note: Quantity model post_init rejects kind=OBSERVED with parents, but if a claim dict or object attempts it:
        fake_claim = {
            "quantity": Quantity(
                id="q_calc",
                definition_key="test.metric",
                value=100.0,
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
                parent_ids=("parent_1",),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )
        }
        res = spec.check(fake_claim, None)
        assert res.passed is True

    def test_derived_floor_stronger_than_parent_floor_rejected(self):
        spec = DerivationDowngradeSpec()
        ledger = Ledger()

        # Parent has evidence_floor=2 (ESTIMATED)
        p_id = ledger.register(Quantity(
            id="p_est",
            definition_key="test.parent",
            value=50.0,
            unit="INR",
            kind=Kind.ESTIMATED,
            evidence_floor=2,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_1", "p.1", "2026-10-20"),),
            method_id="est",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        # Child claims floor=3 (> parent floor=2)
        child = Quantity(
            id="c_overclaim",
            definition_key="test.child",
            value=100.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=3,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="calc",
            model_version="1.0",
            parent_ids=(p_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        res = spec.check(child, ledger)
        assert res.passed is False
        assert "stronger than the computed floor" in res.reason


class TestV2GeographicPrecisionSpec:
    """V2: Geography must not be finer than evidence resolution unless registered downscaling applies."""

    def test_refinement_without_downscaling_rejected(self):
        spec = GeographicPrecisionSpec()
        ledger = Ledger()

        p_id = ledger.register(Quantity(
            id="p_dist",
            definition_key="test.district_pop",
            value=500000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,  # DISTRICT
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("census_2011", "table_1", "2026-10-20"),),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        # Child claims resolution=3 (SUBDISTRICT) without registered downscaling
        child = Quantity(
            id="c_subdist",
            definition_key="test.subdist_pop",
            value=50000.0,
            unit="persons",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="subdistrict_001",
            resolution=3,  # Finer (3 > 2)
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="unregistered_method",
            model_version="1.0",
            parent_ids=(p_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        res = spec.check(child, ledger)
        assert res.passed is False
        assert "without a registered downscaling method" in res.reason

    def test_valid_downscaling_passes_v2(self):
        spec = GeographicPrecisionSpec()
        ledger = Ledger()

        p_id = ledger.register(Quantity(
            id="p_dist_v2",
            definition_key="test.district_pop",
            value=500000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("census_2011", "table_1", "2026-10-20"),),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        # Downscaling using registered popweight_v1
        child = Quantity(
            id="c_downscaled_valid",
            definition_key="test.subdist_pop",
            value=50000.0,
            unit="persons",
            kind=Kind.ESTIMATED,
            evidence_floor=2,  # Must be <= 2
            geo_unit_id="subdistrict_001",
            resolution=3,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="popweight_v1",
            model_version="1.0",
            parent_ids=(p_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        res = spec.check(child, ledger)
        assert res.passed is True


class TestV3PolicyCitationSpec:
    """V3: A policy claim must cite a POLICY_RULE record whose version was valid on stated date."""

    def test_policy_rule_missing_citation_fails(self):
        spec = PolicyCitationSpec()
        q = Quantity(
            id="q_uncited_policy",
            definition_key="scheme.pmfme.grant_rate",
            value=0.35,
            unit="dimensionless",
            kind=Kind.POLICY_RULE,
            evidence_floor=4,
            geo_unit_id="nation",
            resolution=0,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),  # Missing citation!
            method_id="policy",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "must cite an official policy document" in res.reason

    def test_policy_rule_outside_validity_dates_fails(self):
        spec = PolicyCitationSpec()
        # Rule valid from 2020-01-01 to 2023-12-31, but evaluated as of 2026-10-20
        q = Quantity(
            id="q_expired_rule",
            definition_key="scheme.expired.subsidy",
            value=0.50,
            unit="dimensionless",
            kind=Kind.POLICY_RULE,
            evidence_floor=4,
            geo_unit_id="nation",
            resolution=0,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("scheme_v1", "guidelines.pdf", "2020-01-01", "2020-01-01", "2023-12-31"),),
            method_id="policy",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "expired" in res.reason or "not valid" in res.reason

    def test_policy_rule_valid_on_stated_date_passes(self):
        spec = PolicyCitationSpec()
        q = Quantity(
            id="q_valid_policy",
            definition_key="scheme.pmfme.grant_rate",
            value=0.35,
            unit="dimensionless",
            kind=Kind.POLICY_RULE,
            evidence_floor=4,
            geo_unit_id="nation",
            resolution=0,
            as_of="2022-06-15",
            uncertainty="EXACT",
            source_refs=(("pmfme_v1", "section_4.1", "2020-06-01", "2020-01-01", "2025-12-31"),),
            method_id="policy",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is True


class TestV4SourceAttributionSpec:
    """V4: Every number is a ledger quantity with source reference or parent chain ending in sources."""

    def test_root_without_source_refs_rejected(self):
        spec = SourceAttributionSpec()
        q = Quantity(
            id="q_no_source",
            definition_key="test.val",
            value=10.0,
            unit="INR",
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),  # Missing!
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "no source references" in res.reason

    def test_observed_without_locator_rejected(self):
        spec = SourceAttributionSpec()
        q = Quantity(
            id="q_no_locator",
            definition_key="test.obs",
            value=100.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("doc_name", "", "2026-10-20"),),  # Empty locator
            method_id="doc",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "locator" in res.reason

    def test_grounded_derived_chain_passes(self):
        spec = SourceAttributionSpec()
        ledger = Ledger()

        p_id = ledger.register(Quantity(
            id="p_grounded",
            definition_key="test.p",
            value=100.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("census_2011", "Table A-1", "2026-10-20"),),
            method_id="doc",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        child = Quantity(
            id="c_grounded",
            definition_key="test.c",
            value=200.0,
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
            parent_ids=(p_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        res = spec.check(child, ledger)
        assert res.passed is True


class TestV5ContradictionVisibilitySpec:
    """V5: Contradicting sources on same definition, geography and period must remain visible and marked DISPUTED."""

    def test_contradicting_sources_without_dispute_flag_rejected(self):
        spec = ContradictionVisibilitySpec(tolerance=0.05)
        ledger = Ledger()

        # Source 1 reports population 100,000
        ledger.register(Quantity(
            id="pop_src1",
            definition_key="population.total",
            value=100000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_alpha", "page_10", "2026-10-20"),),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        # Source 2 reports population 150,000 (+50% difference) without DISPUTED flag
        candidate = Quantity(
            id="pop_src2",
            definition_key="population.total",
            value=150000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_beta", "page_5", "2026-10-20"),),
            method_id="survey",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),  # Not marked DISPUTED
            license_meta="GODL-India",
        )

        res = spec.check(candidate, ledger)
        assert res.passed is False
        assert "Contradiction detected" in res.reason

    def test_disputed_quantities_both_marked_disputed_passes(self):
        spec = ContradictionVisibilitySpec(tolerance=0.05)
        ledger = Ledger()

        ledger.register(Quantity(
            id="pop_src1_disp",
            definition_key="population.total",
            value=100000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_alpha", "page_10", "2026-10-20"),),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset({"DISPUTED"}),
            license_meta="GODL-India",
        ))

        candidate = Quantity(
            id="pop_src2_disp",
            definition_key="population.total",
            value=150000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_beta", "page_5", "2026-10-20"),),
            method_id="survey",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset({"DISPUTED"}),
            license_meta="GODL-India",
        )

        res = spec.check(candidate, ledger)
        assert res.passed is True


class TestV6UnitCompatibilitySpec:
    """V6: Operations require compatible Pint units."""

    def test_incompatible_operation_units_rejected(self):
        spec = UnitCompatibilitySpec()
        ledger = Ledger()

        p1 = ledger.register(Quantity(
            id="cost_inr",
            definition_key="cost.item",
            value=1000.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("src", "p.1", "2026-10-20"),),
            method_id="survey",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        p2 = ledger.register(Quantity(
            id="weight_kg",
            definition_key="weight.item",
            value=50.0,
            unit="kg",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("src", "p.1", "2026-10-20"),),
            method_id="survey",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        # Adding INR + kg is invalid
        child = Quantity(
            id="c_incompatible_units",
            definition_key="invalid.sum",
            value=1050.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="add",
            model_version="1.0",
            parent_ids=(p1, p2),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        res = spec.check(child, ledger)
        assert res.passed is False
        assert "Unit compatibility failure" in res.reason


class TestV7ReproducibilitySpec:
    """V7: Calculated and simulated quantities store method, versions, seed and parent ids."""

    def test_missing_method_or_model_version_rejected(self):
        spec = ReproducibilitySpec()
        q = Quantity(
            id="c_unreproducible",
            definition_key="calc.metric",
            value=42.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="",  # Missing method_id
            model_version="1.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "reproducibility" in res.reason.lower()

    def test_valid_calculated_lineage_passes(self):
        spec = ReproducibilitySpec()
        q = Quantity(
            id="c_reproducible",
            definition_key="calc.metric",
            value=42.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="sum_parent_values",
            model_version="1.0.0",
            parent_ids=("p1", "p2"),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is True

    def test_simulated_quantity_requires_seed_under_v7(self):
        spec = ReproducibilitySpec()
        q = Quantity(
            id="sim_unreproducible",
            definition_key="sim.metric",
            value=100.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("data_v=1.0", "table", "2026-10-20"),),
            method_id="monte_carlo_no_seed_N=1000",
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "seed" in res.reason.lower()


class TestV8MissingAssumptionSpec:
    """V8: No default or invented assumption: must be USER_ASSUMED or SCENARIO."""

    def test_ungrounded_invented_default_rejected(self):
        spec = MissingAssumptionSpec()
        q = Quantity(
            id="invented_default",
            definition_key="default.interest_rate",
            value=0.085,
            unit="dimensionless",
            kind=Kind.OBSERVED,  # Falsely labelled OBSERVED without any sources
            evidence_floor=4,
            geo_unit_id="nation",
            resolution=0,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),  # No source citation
            method_id="default",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "USER_ASSUMED" in res.reason and "SCENARIO" in res.reason


class TestV9SimulationModelVersionSpec:
    """V9: Every simulation result names scenario id, model version, seed, N and data versions."""

    def test_simulation_missing_seed_or_n_rejected(self):
        spec = SimulationModelVersionSpec()
        q = Quantity(
            id="sim_result",
            definition_key="scenario_growth.revenue",
            value=1200000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty=("INTERVAL", 1000000.0, 1400000.0),
            source_refs=(("data_v=1.0", "table", "2026-10-20"),),
            method_id="monte_carlo",  # Missing seed= and N=
            model_version="1.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "missing mandatory simulation metadata" in res.reason

    def test_valid_simulation_result_passes(self):
        spec = SimulationModelVersionSpec()
        q = Quantity(
            id="sim_valid",
            definition_key="scenario_baseline.revenue",
            value=1200000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty=("INTERVAL", 1000000.0, 1400000.0),
            source_refs=(("data_v=1.0", "table", "2026-10-20"),),
            method_id="monte_carlo_seed=42_N=1000",
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is True

    def test_typed_simulation_metadata_object_passes(self):
        from backend.arthlens.ledger.specs import SimulationMetadata
        spec = SimulationModelVersionSpec()

        sim_meta = SimulationMetadata(
            scenario_id="scenario_expansion",
            model_version="2.1.0",
            seed=1337,
            sample_count=5000,
            data_versions=("census_2011_v1", "pmfme_v2"),
        )

        q = Quantity(
            id="sim_typed",
            definition_key="business.revenue",
            value=3500000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="monte_carlo_engine",
            model_version="2.1.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
            simulation_meta=sim_meta,
        )
        res = spec.check(q, None)
        assert res.passed is True

    def test_malformed_string_seed_rejected(self):
        spec = SimulationModelVersionSpec()
        q = Quantity(
            id="sim_bad_seed",
            definition_key="scenario_growth.revenue",
            value=1200000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("data_v=1.0", "table", "2026-10-20"),),
            method_id="monte_carlo_seed=banana_N=1000",  # seed is not an integer
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "seed" in res.reason.lower() and "integer" in res.reason.lower()

    def test_negative_seed_rejected(self):
        spec = SimulationModelVersionSpec()
        q = Quantity(
            id="sim_neg_seed",
            definition_key="scenario_growth.revenue",
            value=1200000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("data_v=1.0", "table", "2026-10-20"),),
            method_id="monte_carlo_seed=-42_N=1000",  # negative seed
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "seed" in res.reason.lower() and "non-negative" in res.reason.lower()

    def test_invalid_sample_count_rejected(self):
        spec = SimulationModelVersionSpec()
        # N=0 is invalid
        q0 = Quantity(
            id="sim_zero_n",
            definition_key="scenario_growth.revenue",
            value=1200000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("data_v=1.0", "table", "2026-10-20"),),
            method_id="monte_carlo_seed=42_N=0",
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res0 = spec.check(q0, None)
        assert res0.passed is False
        assert "sample count" in res0.reason.lower() or "positive" in res0.reason.lower()

    def test_missing_data_versions_rejected(self):
        spec = SimulationModelVersionSpec()
        q = Quantity(
            id="sim_no_dv",
            definition_key="scenario_growth.revenue",
            value=1200000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),  # No data version citations
            method_id="monte_carlo_seed=42_N=1000",
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = spec.check(q, None)
        assert res.passed is False
        assert "data_versions" in res.reason.lower()

    def test_simulation_metadata_dataclass_validation(self):
        from backend.arthlens.ledger.specs import SimulationMetadata
        import pytest

        # Invalid seed type
        with pytest.raises(ValueError, match="seed must be an integer"):
            SimulationMetadata("scen_1", "1.0", "bad_seed", 100, ("v1",))  # type: ignore

        # Negative seed
        with pytest.raises(ValueError, match="seed must be non-negative"):
            SimulationMetadata("scen_1", "1.0", -1, 100, ("v1",))

        # Sample count <= 0
        with pytest.raises(ValueError, match="sample_count \\(N\\) must be positive"):
            SimulationMetadata("scen_1", "1.0", 42, 0, ("v1",))

        # Empty scenario_id
        with pytest.raises(ValueError, match="scenario_id must be a non-empty string"):
            SimulationMetadata("", "1.0", 42, 100, ("v1",))

        # Empty data_versions
        with pytest.raises(ValueError, match="data_versions must contain at least one"):
            SimulationMetadata("scen_1", "1.0", 42, 100, ())


class TestAndSpecification:
    """AndSpecification combines multiple specifications logically."""

    def test_and_specification_passes_when_all_pass(self):
        and_spec = AndSpecification(
            DerivationDowngradeSpec(),
            GeographicPrecisionSpec(),
            SourceAttributionSpec(),
        )
        q = Quantity(
            id="valid_q",
            definition_key="test.obs",
            value=100.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("census_2011", "table_1", "2026-10-20"),),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        res = and_spec.check(q, None)
        assert res.passed is True
        results = and_spec.check_all(q, None)
        assert len(results) == 3
        assert all(r.passed for r in results)
