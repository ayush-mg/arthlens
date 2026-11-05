"""
Atlas Quality Shading Presentation Adapter and GeoJSON Styler (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 10.2, Part 13.1 P2-3).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).

Acceptance Criterion:
Atlas shades quality states correctly.

Presentation Layer Contract:
1. Consumes evaluated IndicatorQualityAssessment instances directly (zero re-evaluation).
2. Generates deterministic MapLibre GL JS / Leaflet GeoJSON layer properties.
3. Produces MapLibre data-driven paint expressions for choropleths and quality overlays.
4. Generates an interactive visual HTML/SVG rendering artifact for verification.
"""

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional, Sequence

from backend.arthlens.quality.evaluator import IndicatorQualityAssessment
from backend.arthlens.quality.vocabulary import (
    ATLAS_SHADING_TOKENS,
    AtlasShadingToken,
    CalculationSuitability,
    QualityStatus,
)


def get_maplibre_quality_paint_properties() -> Dict[str, Any]:
    """
    Generate authoritative MapLibre GL JS data-driven paint expression for data-quality layer.
    Handbook Reference: Part 10.2.
    """
    fill_color_expr: List[Any] = ["match", ["get", "quality_status"]]
    opacity_expr: List[Any] = ["match", ["get", "quality_status"]]

    for status, token in ATLAS_SHADING_TOKENS.items():
        fill_color_expr.extend([status.value, token.hex_color])
        opacity_expr.extend([status.value, token.fill_opacity])

    # Fallback to UNAVAILABLE
    fill_color_expr.append(ATLAS_SHADING_TOKENS[QualityStatus.UNAVAILABLE].hex_color)
    opacity_expr.append(ATLAS_SHADING_TOKENS[QualityStatus.UNAVAILABLE].fill_opacity)

    return {
        "fill-color": fill_color_expr,
        "fill-opacity": opacity_expr,
        "fill-outline-color": "#1E293B",  # Slate 800 boundary line
    }


class AtlasQualityShadingAdapter:
    """
    Presentation adapter transforming domain quality assessments into MapLibre / GeoJSON
    visualization payloads for Atlas screens.
    """

    @classmethod
    def apply_quality_shading_to_feature(
        cls,
        feature: Dict[str, Any],
        assessment: IndicatorQualityAssessment,
    ) -> Dict[str, Any]:
        """
        Decorate a GeoJSON feature with quality shading presentation properties.
        Strictly consumes pre-evaluated assessment.
        """
        props = dict(feature.get("properties") or {})
        token = assessment.shading

        props["quality_status"] = assessment.primary_status.value
        props["quality_label"] = token.label
        props["quality_color"] = token.hex_color
        props["quality_color_token"] = token.color_token
        props["quality_fill_opacity"] = token.fill_opacity
        props["quality_stroke_style"] = token.stroke_style
        props["quality_pattern"] = token.pattern
        props["quality_explanation"] = assessment.explanation
        props["quality_suitability"] = assessment.suitability.value
        props["observation_date"] = assessment.as_of
        props["is_stale"] = assessment.is_stale
        props["staleness_reason"] = assessment.staleness_explanation or ""

        updated = dict(feature)
        updated["properties"] = props
        return updated

    @classmethod
    def create_quality_geojson_collection(
        cls,
        features_with_assessments: Sequence[tuple],  # (feature_dict, assessment)
    ) -> Dict[str, Any]:
        """Convert a sequence of (feature, assessment) pairs into a shaded FeatureCollection."""
        shaded_features = [
            cls.apply_quality_shading_to_feature(feat, assess)
            for feat, assess in features_with_assessments
        ]
        return {
            "type": "FeatureCollection",
            "features": shaded_features,
            "metadata": {
                "layer": "data_quality_overlay",
                "legend": {
                    status.value: {
                        "label": token.label,
                        "color": token.hex_color,
                        "color_token": token.color_token,
                        "pattern": token.pattern,
                        "stroke": token.stroke_style,
                    }
                    for status, token in ATLAS_SHADING_TOKENS.items()
                },
            },
        }

    @classmethod
    def generate_html_preview(
        cls,
        assessments: Sequence[IndicatorQualityAssessment],
        title: str = "ArthLens Atlas — Data-Quality Shading Preview (P2-3)",
    ) -> str:
        """
        Generate a self-contained interactive visual HTML preview of the Atlas quality overlay.
        Renders the five quality states with their exact design tokens, patterns, and explanations.
        """
        cards_html = []
        for assess in assessments:
            token = assess.shading
            stroke_css = "solid" if token.stroke_style == "solid" else "dashed"
            cards_html.append(f"""
            <div class="quality-card" style="border-left: 8px {stroke_css} {token.hex_color};">
                <div class="card-header">
                    <span class="geo-id">{assess.geo_unit_id}</span>
                    <span class="badge" style="background-color: {token.hex_color}; color: #ffffff;">{token.label}</span>
                </div>
                <div class="card-body">
                    <p><strong>Indicator:</strong> <code>{assess.indicator_key}</code></p>
                    <p><strong>Primary Status:</strong> <span class="status-token token-{token.color_token}">{assess.primary_status.value}</span></p>
                    <p><strong>Hex Color:</strong> <code>{token.hex_color}</code> | <strong>Opacity:</strong> {token.fill_opacity}</p>
                    <p><strong>Observation Date (as_of):</strong> {assess.as_of or 'None'}</p>
                    <p><strong>Calculation Suitability:</strong> <code>{assess.suitability.value}</code></p>
                    <p class="explanation"><strong>Explanation:</strong> {assess.explanation}</p>
                    {f'<p class="staleness-note"><strong>Staleness Audit:</strong> {assess.staleness_explanation}</p>' if assess.staleness_explanation else ''}
                </div>
                <div class="swatch" style="background-color: {token.hex_color}; opacity: {token.fill_opacity};">
                    <span>{token.pattern} / {token.stroke_style}</span>
                </div>
            </div>
            """)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        h1 {{ margin-bottom: 8px; font-size: 24px; color: #38bdf8; }}
        p.subtitle {{ color: #94a3b8; margin-top: 0; margin-bottom: 24px; font-size: 14px; }}
        .legend {{ display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; background: #1e293b; padding: 16px; border-radius: 8px; }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 4px; border: 1px solid #475569; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
        .quality-card {{ background: #1e293b; border-radius: 8px; padding: 16px; position: relative; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
        .geo-id {{ font-weight: bold; font-size: 15px; color: #f1f5f9; }}
        .badge {{ padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
        .card-body p {{ margin: 6px 0; font-size: 13px; color: #cbd5e1; }}
        code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #38bdf8; }}
        .explanation {{ color: #e2e8f0; font-size: 12px; background: #0f172a; padding: 8px; border-radius: 6px; margin-top: 8px; }}
        .staleness-note {{ color: #fdba74; font-size: 12px; background: #431407; padding: 8px; border-radius: 6px; }}
        .swatch {{ height: 28px; border-radius: 4px; margin-top: 12px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; color: #000; text-transform: uppercase; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="subtitle">Authoritative Atlas Quality Overlay Shading (Handbook Part 7.5 Step 10 & Part 10.2). Verifies deterministic color assignment across all quality states.</p>
    <div class="legend">
        {''.join(f'<div class="legend-item"><div class="legend-color" style="background:{t.hex_color};"></div><span><strong>{t.status.value}:</strong> {t.label}</span></div>' for t in ATLAS_SHADING_TOKENS.values())}
    </div>
    <div class="grid">
        {''.join(cards_html)}
    </div>
</body>
</html>"""
        return html
