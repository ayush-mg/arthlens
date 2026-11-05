"""
Unit Tests for Atlas Quality Shading Presentation Contract and GeoJSON Styler (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 10.2, Part 13.1 P2-3).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).

Acceptance Criterion:
Atlas shades quality states correctly.
"""

import json
import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.evaluator import DataQualityEvaluator
from backend.arthlens.quality.shading import (
    AtlasQualityShadingAdapter,
    get_maplibre_quality_paint_properties,
)
from backend.arthlens.quality.vocabulary import (
    ATLAS_SHADING_TOKENS,
    AtlasShadingToken,
    CalculationSuitability,
    QualityStatus,
)


class TestAtlasQualityShading:
    """Tests verifying that Atlas quality states are shaded correctly."""

    @pytest.fixture
    def evaluator(self):
        return DataQualityEvaluator(evaluation_date="2026-11-06")

    def test_every_status_has_a_stable_presentation_contract(self):
        """Verify tokens, labels, hex colors, and stroke styles across all 5 states."""
        for status in QualityStatus:
            token = ATLAS_SHADING_TOKENS[status]
            assert isinstance(token, AtlasShadingToken)
            assert token.status == status
            assert token.hex_color.startswith("#")
            assert token.label
            assert token.color_token
            assert token.stroke_style
            assert token.pattern
            assert isinstance(token.default_suitability, CalculationSuitability)

    def test_exact_hex_colors_for_quality_states(self):
        """Exact hex color tokens required by Atlas design system."""
        assert ATLAS_SHADING_TOKENS[QualityStatus.CURRENT].hex_color == "#22C55E"      # Emerald Green
        assert ATLAS_SHADING_TOKENS[QualityStatus.INCOMPLETE].hex_color == "#EAB308"   # Amber Yellow
        assert ATLAS_SHADING_TOKENS[QualityStatus.STALE].hex_color == "#F97316"        # Warm Orange
        assert ATLAS_SHADING_TOKENS[QualityStatus.ESTIMATED].hex_color == "#3B82F6"    # Electric Blue
        assert ATLAS_SHADING_TOKENS[QualityStatus.UNAVAILABLE].hex_color == "#94A3B8"  # Slate Gray

    def test_maplibre_data_driven_paint_properties(self):
        """Paint properties must map each quality_status string to its exact color and opacity."""
        paint = get_maplibre_quality_paint_properties()
        assert "fill-color" in paint
        assert "fill-opacity" in paint

        fill_color_expr = paint["fill-color"]
        assert fill_color_expr[0] == "match"
        assert fill_color_expr[1] == ["get", "quality_status"]

        # Check all 5 statuses exist in the expression
        for status, token in ATLAS_SHADING_TOKENS.items():
            idx = fill_color_expr.index(status.value)
            assert fill_color_expr[idx + 1] == token.hex_color

    def test_apply_quality_shading_to_geojson_feature(self, evaluator):
        """GeoJSON feature is decorated with evaluated quality shading attributes."""
        feature = {
            "type": "Feature",
            "properties": {
                "DISTRICT": "Prayagraj",
                "lgd_code": "120",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[81.5, 24.5], [82.5, 24.5], [82.5, 25.5], [81.5, 25.5], [81.5, 24.5]]],
            },
        }

        # Stale census quantity
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
        assessment = evaluator.evaluate_quantity(q_census, "population.total", "in:district:120")

        shaded = AtlasQualityShadingAdapter.apply_quality_shading_to_feature(feature, assessment)
        props = shaded["properties"]

        # Shading matches evaluated STALE status
        assert props["quality_status"] == "STALE"
        assert props["quality_color"] == "#F97316"
        assert props["quality_color_token"] == "atlas-quality-stale"
        assert props["quality_stroke_style"] == "hatched"
        assert props["is_stale"] is True
        assert "exceeds maximum threshold" in props["staleness_reason"].lower()
        # Original properties preserved
        assert props["DISTRICT"] == "Prayagraj"
        assert props["lgd_code"] == "120"

    def test_unavailable_never_appears_as_current(self, evaluator):
        """An unavailable indicator is shaded Gray #94A3B8, never Green #22C55E."""
        feature = {"type": "Feature", "properties": {"DISTRICT": "Varanasi", "lgd_code": "187"}}
        assessment = evaluator.evaluate_quantity(None, "unemployment_rate", "in:district:187")

        shaded = AtlasQualityShadingAdapter.apply_quality_shading_to_feature(feature, assessment)
        props = shaded["properties"]

        assert props["quality_status"] == "UNAVAILABLE"
        assert props["quality_color"] == "#94A3B8"
        assert props["quality_color"] != "#22C55E"
        assert props["quality_status"] != "CURRENT"

    def test_html_visual_preview_generation(self, evaluator):
        """Generate self-contained HTML visual preview representing all 5 quality states."""
        # 1. Current
        q_curr = Quantity(id="q1", definition_key="recent.demographic_sample", value=150.0, unit="dim", kind=Kind.OBSERVED, evidence_floor=4, geo_unit_id="in:district:120", resolution=2, as_of="2026-10-01", source_refs=("DS-05",))
        # 2. Incomplete
        q_inc = Quantity(id="q2", definition_key="tehsil_pop", value=100.0, unit="persons", kind=Kind.OBSERVED, evidence_floor=4, geo_unit_id="in:district:120", resolution=2, as_of="2026-10-01", source_refs=("DS-05",))
        # 3. Stale
        q_stale = Quantity(id="q3", definition_key="population.total", value=5954391.0, unit="persons", kind=Kind.OBSERVED, evidence_floor=4, geo_unit_id="in:district:120", resolution=2, as_of="2011-03-01", source_refs=("DS-05",), quality_flags=frozenset({"STALE"}))
        # 4. Estimated
        q_est = Quantity(id="q4", definition_key="demand.projected", value=90000.0, unit="INR", kind=Kind.ESTIMATED, evidence_floor=2, geo_unit_id="in:district:120", resolution=2, as_of="2026-10-01")

        a_curr = evaluator.evaluate_quantity(q_curr, "recent.demographic_sample", "in:district:120")
        a_inc = evaluator.evaluate_quantity(q_inc, "tehsil_pop", "in:district:120", expected_subunits=["s1", "s2"], actual_subunits=["s1"])
        a_stale = evaluator.evaluate_quantity(q_stale, "population.total", "in:district:120")
        a_est = evaluator.evaluate_quantity(q_est, "demand.projected", "in:district:120")
        a_unavail = evaluator.evaluate_quantity(None, "soil.fertility", "in:district:120")

        all_assessments = [a_curr, a_inc, a_stale, a_est, a_unavail]
        html = AtlasQualityShadingAdapter.generate_html_preview(all_assessments)

        assert "<!DOCTYPE html>" in html
        assert "#22C55E" in html  # Current color
        assert "#EAB308" in html  # Incomplete color
        assert "#F97316" in html  # Stale color
        assert "#3B82F6" in html  # Estimated color
        assert "#94A3B8" in html  # Unavailable color
        assert "CURRENT" in html
        assert "INCOMPLETE" in html
        assert "STALE" in html
        assert "ESTIMATED" in html
        assert "UNAVAILABLE" in html
