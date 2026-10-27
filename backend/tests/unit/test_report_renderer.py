"""
Unit tests for ReportRenderer and Free-Number Scanner (Rule G4: Ledger-Only Rendering).

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.6, 4.7).
Phase: P1-4 (Verification Specifications, LedgerVerifier, ReportRenderer).
"""

import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.renderer import AllowlistConfig, ReportRenderer


class TestReportRenderer:
    """Verify placeholder substitution and free-number rejection."""

    @pytest.fixture
    def populated_ledger(self) -> Ledger:
        ledger = Ledger()
        # Population quantity with as_of='2026-10-20'
        ledger.register(Quantity(
            id="q_pop_001",
            definition_key="census.population.total",
            value=250000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,  # DISTRICT
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("census_2011", "Table A-1", "2026-10-20"),),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))
        # Subsidy amount
        ledger.register(Quantity(
            id="q_subsidy_002",
            definition_key="scheme.pmfme.grant",
            value=100000.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("pmfme_guidelines", "Section 4.1", "2026-10-20"),),
            method_id="guideline",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))
        return ledger

    def test_valid_placeholders_resolve_to_formatted_chips(self, populated_ledger):
        renderer = ReportRenderer()
        template = "The district population is {{q:q_pop_001}} and eligible subsidy is {{q:q_subsidy_002}}."

        result = renderer.render(template, populated_ledger)
        assert result.passed is True
        assert bool(result) is True
        assert len(result.free_numbers) == 0
        assert len(result.resolved_quantities) == 2
        assert "250,000 persons [OBSERVED | DISTRICT | 2026-10-20 | evidence_graph:q_pop_001]" in result.rendered_text
        assert "100,000 INR [OBSERVED | DISTRICT | 2026-10-20 | evidence_graph:q_subsidy_002]" in result.rendered_text

    def test_unknown_placeholder_rejected(self, populated_ledger):
        renderer = ReportRenderer()
        template = "The population is {{q:non_existent_uuid}}."

        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert "references unknown quantity ID" in result.rejection_reason

    def test_unsupported_free_number_rejected(self, populated_ledger):
        """Rule G4: The LLM must not type free digits for results."""
        renderer = ReportRenderer()
        # An unverified numeric literal 500000 typed directly by the LLM
        template = "The population is {{q:q_pop_001}} and estimated cost is 500000 INR."

        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert len(result.free_numbers) > 0
        assert "500000" in result.free_numbers
        assert "Free number scanner rejected report" in result.rejection_reason

    def test_unsupported_percentage_literal_rejected(self, populated_ledger):
        renderer = ReportRenderer()
        template = "Under the scheme, subsidy is {{q:q_subsidy_002}} and equity requirement is 35%."

        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("35" in fn for fn in result.free_numbers)

    def test_unsupported_currency_literal_rejected(self, populated_ledger):
        renderer = ReportRenderer()
        template = "Total capital required is ₹750000."

        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("750000" in fn for fn in result.free_numbers)

    def test_allowlisted_ledger_years_permitted(self, populated_ledger):
        """Years appearing in a ledger quantity's as_of/period are permitted."""
        renderer = ReportRenderer()
        # '2026' is the year of q_pop_001's as_of ('2026-10-20')
        template = "In 2026, the district population was {{q:q_pop_001}}."

        result = renderer.render(template, populated_ledger)
        assert result.passed is True
        assert len(result.free_numbers) == 0

    def test_allowlisted_section_numbers_permitted(self, populated_ledger):
        """Section numbers (e.g. Section 4.5, Part 1) are permitted."""
        renderer = ReportRenderer()
        template = "According to Section 4.5, the population is {{q:q_pop_001}}."

        result = renderer.render(template, populated_ledger)
        assert result.passed is True
        assert len(result.free_numbers) == 0

    def test_allowlisted_list_indices_permitted(self, populated_ledger):
        """List indices (1., 2., [1], (1)) are permitted."""
        renderer = ReportRenderer()
        template = (
            "Key findings:\n"
            "1. Population is {{q:q_pop_001}}.\n"
            "2. Subsidy is {{q:q_subsidy_002}}."
        )

        result = renderer.render(template, populated_ledger)
        assert result.passed is True
        assert len(result.free_numbers) == 0

    def test_quoted_source_passage_numbers_permitted(self, populated_ledger):
        """Text in a quoted source passage is shown as a quote with its locator; numbers in it are not treated as results."""
        renderer = ReportRenderer()
        # Quoted document passage containing numbers and proper locator
        template = (
            'According to the guidelines, "The unit requires at least 15 skilled workers" '
            '(Handbook, p. 12). The total subsidy is {{q:q_subsidy_002}}.'
        )

        result = renderer.render(template, populated_ledger)
        assert result.passed is True
        assert len(result.free_numbers) == 0
        assert "15" not in result.free_numbers

    def test_unsupported_negative_numbers_and_decimals_rejected(self, populated_ledger):
        renderer = ReportRenderer()
        template = "Operating deficit was -500 INR and margin dropped by -12.5%."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("-500" in fn for fn in result.free_numbers)
        assert any("-12.5" in fn for fn in result.free_numbers)

    def test_unsupported_indian_comma_numbers_rejected(self, populated_ledger):
        renderer = ReportRenderer()
        template = "Sanctioned grant pool is 1,00,000 INR and turnover exceeds 15,00,000."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("1,00,000" in fn for fn in result.free_numbers)
        assert any("15,00,000" in fn for fn in result.free_numbers)

    def test_unsupported_comma_separated_decimals_rejected(self, populated_ledger):
        renderer = ReportRenderer()
        template = "The exact fee assessed was 1,234.56 INR."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("1,234.56" in fn for fn in result.free_numbers)

    def test_unsupported_currency_and_percentage_symbols_rejected(self, populated_ledger):
        renderer = ReportRenderer()
        template = "Total required equity is ₹50,000 representing 25% of project cost."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("50,000" in fn for fn in result.free_numbers)
        assert any("25" in fn for fn in result.free_numbers)

    def test_arbitrary_quoted_claims_without_locator_rejected(self, populated_ledger):
        """Arbitrary quotes without valid passage locators cannot bypass free-number scanning."""
        renderer = ReportRenderer()
        template = (
            'According to unverified remarks, "the unit achieved 500000 INR revenue" '
            'without official audit. Subsidy is {{q:q_subsidy_002}}.'
        )
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("500000" in fn for fn in result.free_numbers)
        assert "Free number scanner rejected report" in result.rejection_reason

    def test_malformed_placeholder_syntax_rejected(self, populated_ledger):
        """Malformed placeholders like {{q:}}, {{q}}, {{ q:   }} must be rejected."""
        renderer = ReportRenderer()

        # Missing ID
        res1 = renderer.render("Value is {{q:}}.", populated_ledger)
        assert res1.passed is False
        assert any("Malformed quantity placeholder" in err for err in res1.errors)

        # Missing colon / ID
        res2 = renderer.render("Value is {{q}}.", populated_ledger)
        assert res2.passed is False
        assert any("Malformed quantity placeholder" in err for err in res2.errors)

        # Whitespace-only ID
        res3 = renderer.render("Value is {{ q:   }}.", populated_ledger)
        assert res3.passed is False
        assert any("Malformed quantity placeholder" in err for err in res3.errors)

        # Wrong prefix
        res4 = renderer.render("Value is {{quantity:q_pop_001}}.", populated_ledger)
        assert res4.passed is False
        assert any("Malformed quantity placeholder" in err for err in res4.errors)

    def test_unverified_quantity_placeholder_rejected(self, populated_ledger):
        """If a quantity exists in the ledger but fails verifier checks, rendering must be rejected."""
        renderer = ReportRenderer()
        # Register an invalid quantity (Kind.OBSERVED without any source_refs)
        populated_ledger.register(Quantity(
            id="q_invalid_unattributed",
            definition_key="test.unattributed",
            value=777.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),  # Missing source citation violates V4
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        ))

        template = "The result is {{q:q_invalid_unattributed}}."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("failed verification" in err for err in result.errors)
        assert "q_invalid_unattributed" in result.rejection_reason

    def test_table_and_figure_references_permitted(self, populated_ledger):
        """Structural table and figure numbers (Table 1, Figure 2.1) are permitted."""
        renderer = ReportRenderer()
        template = "As shown in Table 1 and Figure 2.1, the population is {{q:q_pop_001}}."
        result = renderer.render(template, populated_ledger)
        assert result.passed is True
        assert len(result.free_numbers) == 0

    def test_concealed_claim_in_section_heading_rejected(self, populated_ledger):
        """Unsupported claims concealed inside section headings must be detected."""
        renderer = ReportRenderer()
        template = "### Section 1. Overview: Target is 500000 beneficiaries\nPopulation is {{q:q_pop_001}}."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("500000" in fn for fn in result.free_numbers)
        assert "1" not in result.free_numbers  # Section 1 itself was allowlisted

    def test_concealed_claim_in_numbered_list_rejected(self, populated_ledger):
        """Unsupported claims inside numbered list lines must be detected."""
        renderer = ReportRenderer()
        template = (
            "Program milestones:\n"
            "1. Verified census population is {{q:q_pop_001}}.\n"
            "2. Expected unverified expansion of 25000 units."
        )
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("25000" in fn for fn in result.free_numbers)
        assert "1" not in result.free_numbers
        assert "2" not in result.free_numbers

    def test_concealed_claim_in_table_reference_rejected(self, populated_ledger):
        """Unsupported claims in table reference sentences must be detected."""
        renderer = ReportRenderer()
        template = "Table 1 indicates that 45000 enterprises applied for relief."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("45000" in fn for fn in result.free_numbers)
        assert "1" not in result.free_numbers

    def test_concealed_claim_in_year_context_rejected(self, populated_ledger):
        """Supported year is allowed, but unverified claims next to it must be rejected."""
        renderer = ReportRenderer()
        # 2026 is supported from populated_ledger q_pop_001
        template = "In 2026, the company recorded 999 unverified sales."
        result = renderer.render(template, populated_ledger)
        assert result.passed is False
        assert any("999" in fn for fn in result.free_numbers)
        assert "2026" not in result.free_numbers
