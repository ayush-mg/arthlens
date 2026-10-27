"""
Unit tests for LedgerVerifier orchestration and VerificationReport.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.5, 5.1).
Phase: P1-4 (Verification Specifications, LedgerVerifier, ReportRenderer).
"""

import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.specs import DerivationDowngradeSpec, GeographicPrecisionSpec
from backend.arthlens.ledger.verifier import LedgerVerifier, VerificationReport


class TestLedgerVerifier:
    """Verify LedgerVerifier orchestration behavior."""

    def test_default_verifier_has_nine_specifications(self):
        verifier = LedgerVerifier()
        assert len(verifier.specifications) == 9

    def test_custom_verifier_with_subset(self):
        verifier = LedgerVerifier(specs=[DerivationDowngradeSpec(), GeographicPrecisionSpec()])
        assert len(verifier.specifications) == 2

    def test_verify_quantity_clean_passes(self):
        verifier = LedgerVerifier()
        ledger = Ledger()

        q = Quantity(
            id="q_clean",
            definition_key="census.pop",
            value=10000.0,
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
        )
        ledger.register(q)

        report = verifier.verify_quantity(q, ledger)
        assert report.passed is True
        assert bool(report) is True
        assert len(report.failures) == 0
        assert len(report.results) == 9
        assert "passed all 9" in report.summary

    def test_verify_ledger_detects_violations_and_reports_offending_ids(self):
        verifier = LedgerVerifier()
        ledger = Ledger()

        # Valid root
        p1 = ledger.register(Quantity(
            id="p_valid",
            definition_key="test.valid",
            value=100.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_1", "p.1", "2026-10-20"),),
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        # Root missing source refs (violates V4)
        p2 = ledger.register(Quantity(
            id="p_missing_source",
            definition_key="test.missing_src",
            value=200.0,
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
        ))

        report = verifier.verify_ledger(ledger)
        assert report.passed is False
        assert bool(report) is False
        assert len(report.failures) >= 1
        assert "p_missing_source" in report.offending_quantity_ids

    def test_verification_is_deterministic(self):
        """Identical inputs and ledger state produce identical verification results."""
        verifier = LedgerVerifier()
        ledger = Ledger()

        q = Quantity(
            id="q_deter",
            definition_key="test.metric",
            value=500.0,
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
        ledger.register(q)

        report1 = verifier.verify_quantity(q, ledger)
        report2 = verifier.verify_quantity(q, ledger)

        assert report1.passed == report2.passed
        assert report1.summary == report2.summary
        assert len(report1.results) == len(report2.results)
        for r1, r2 in zip(report1.results, report2.results):
            assert r1.passed == r2.passed
            assert r1.spec_name == r2.spec_name
            assert r1.reason == r2.reason
