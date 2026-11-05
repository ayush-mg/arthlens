"""
ArthLens Data-Quality Layer and Staleness Flags Module (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 7.5 Step 10, Part 10.2, Part 13.1 P2-3).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).
"""

from backend.arthlens.quality.evaluator import (
    DataQualityEvaluator,
    IndicatorQualityAssessment,
)
from backend.arthlens.quality.freshness import (
    FreshnessEvaluation,
    FreshnessPolicy,
    FreshnessRegistry,
    evaluate_staleness,
)
from backend.arthlens.quality.propagation import (
    CalculationQualityContext,
    GatedCalculationError,
    inspect_calculation_inputs,
)
from backend.arthlens.quality.shading import (
    AtlasQualityShadingAdapter,
    get_maplibre_quality_paint_properties,
)
from backend.arthlens.quality.vocabulary import (
    ATLAS_SHADING_TOKENS,
    AtlasShadingToken,
    CalculationSuitability,
    QualityIssue,
    QualityStatus,
    get_shading_token,
    resolve_primary_status,
)

__all__ = [
    "QualityStatus",
    "CalculationSuitability",
    "QualityIssue",
    "AtlasShadingToken",
    "ATLAS_SHADING_TOKENS",
    "resolve_primary_status",
    "get_shading_token",
    "FreshnessPolicy",
    "FreshnessRegistry",
    "FreshnessEvaluation",
    "evaluate_staleness",
    "IndicatorQualityAssessment",
    "DataQualityEvaluator",
    "CalculationQualityContext",
    "GatedCalculationError",
    "inspect_calculation_inputs",
    "AtlasQualityShadingAdapter",
    "get_maplibre_quality_paint_properties",
]
