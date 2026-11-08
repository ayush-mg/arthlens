"""
Quality Vocabulary, Design Tokens, and Precedence Rules for Data-Quality Layer (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 7.5 Step 10, Part 10.2, Part 13.1 P2-3).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).

Acceptance Criterion:
Atlas shades quality states correctly.

Vocabulary:
- CURRENT: Data is observed, fresh, complete, and within configured maximum age.
- INCOMPLETE: Data exists but has missing attributes, partial sub-unit coverage, or unresolved dimensions.
- STALE: Data is observed and complete, but its observation period (as_of) exceeds the maximum allowed age.
- ESTIMATED: Data is modelled, downscaled, or synthetic rather than directly observed.
- UNAVAILABLE: Data does not exist or cannot be retrieved; never represented as silent numeric zero.

Precedence for Primary Display State:
UNAVAILABLE > INCOMPLETE > STALE > ESTIMATED > CURRENT
All applicable secondary issues and explanations are preserved.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence, Union


class QualityStatus(str, Enum):
    """
    Standard quality vocabulary published by ArthLens data pipelines and Atlas.
    Handbook Reference: Part 7.5 Step 10, Part 10.2, Part 13.1 P2-3.
    """
    CURRENT = "CURRENT"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"
    CONTRADICTED = "CONTRADICTED"


class CalculationSuitability(str, Enum):
    """
    Downstream calculation suitability and decision-gating flags.
    Handbook Reference: Part 4.4, Part 7.4.
    """
    SUITABLE_CURRENT = "SUITABLE_CURRENT"
    CAUTION_PARTIAL = "CAUTION_PARTIAL"
    SUITABLE_HISTORICAL_ONLY = "SUITABLE_HISTORICAL_ONLY"
    ESTIMATED_PROJECTION = "ESTIMATED_PROJECTION"
    UNSUITABLE_MISSING = "UNSUITABLE_MISSING"
    UNSUITABLE_CONTRADICTED = "UNSUITABLE_CONTRADICTED"


@dataclass(frozen=True)
class QualityIssue:
    """
    Detailed individual quality finding or anomaly associated with an indicator.
    Allows preserving all simultaneous issues when a primary status is presented.
    """
    status: QualityStatus
    reason: str
    dimension: str = "general"
    severity: str = "WARNING"  # INFO, WARNING, BLOCKING


@dataclass(frozen=True)
class AtlasShadingToken:
    """
    Deterministic presentation contract for Atlas choropleth / quality overlay shading.
    Provides stable design tokens, hex codes, patterns, and display text.
    """
    status: QualityStatus
    label: str
    color_token: str
    hex_color: str
    fill_opacity: float
    stroke_style: str  # solid, dashed, hatched, dotted, diagonal-cross
    pattern: str
    default_suitability: CalculationSuitability


# Deterministic presentation design tokens
ATLAS_SHADING_TOKENS: Dict[QualityStatus, AtlasShadingToken] = {
    QualityStatus.CURRENT: AtlasShadingToken(
        status=QualityStatus.CURRENT,
        label="Current Data",
        color_token="atlas-quality-current",
        hex_color="#22C55E",  # Emerald Green
        fill_opacity=0.65,
        stroke_style="solid",
        pattern="none",
        default_suitability=CalculationSuitability.SUITABLE_CURRENT,
    ),
    QualityStatus.INCOMPLETE: AtlasShadingToken(
        status=QualityStatus.INCOMPLETE,
        label="Incomplete Coverage",
        color_token="atlas-quality-incomplete",
        hex_color="#EAB308",  # Amber Yellow
        fill_opacity=0.60,
        stroke_style="dashed",
        pattern="stripes-light",
        default_suitability=CalculationSuitability.CAUTION_PARTIAL,
    ),
    QualityStatus.STALE: AtlasShadingToken(
        status=QualityStatus.STALE,
        label="Stale Observation",
        color_token="atlas-quality-stale",
        hex_color="#F97316",  # Warm Orange
        fill_opacity=0.70,
        stroke_style="hatched",
        pattern="hatch-diagonal",
        default_suitability=CalculationSuitability.SUITABLE_HISTORICAL_ONLY,
    ),
    QualityStatus.ESTIMATED: AtlasShadingToken(
        status=QualityStatus.ESTIMATED,
        label="Estimated / Modelled",
        color_token="atlas-quality-estimated",
        hex_color="#3B82F6",  # Electric Blue
        fill_opacity=0.60,
        stroke_style="dotted",
        pattern="dots",
        default_suitability=CalculationSuitability.ESTIMATED_PROJECTION,
    ),
    QualityStatus.UNAVAILABLE: AtlasShadingToken(
        status=QualityStatus.UNAVAILABLE,
        label="Data Unavailable",
        color_token="atlas-quality-unavailable",
        hex_color="#94A3B8",  # Slate Gray
        fill_opacity=0.45,
        stroke_style="diagonal-cross",
        pattern="cross-hatch",
        default_suitability=CalculationSuitability.UNSUITABLE_MISSING,
    ),
    QualityStatus.CONTRADICTED: AtlasShadingToken(
        status=QualityStatus.CONTRADICTED,
        label="Contradicted Sources",
        color_token="atlas-quality-contradicted",
        hex_color="#DC2626",  # Crimson Red
        fill_opacity=0.75,
        stroke_style="dashed",
        pattern="cross-hatch",
        default_suitability=CalculationSuitability.UNSUITABLE_CONTRADICTED,
    ),
}

# Strict deterministic precedence order for primary display state selection
PRECEDENCE_ORDER: List[QualityStatus] = [
    QualityStatus.UNAVAILABLE,
    QualityStatus.CONTRADICTED,
    QualityStatus.INCOMPLETE,
    QualityStatus.STALE,
    QualityStatus.ESTIMATED,
    QualityStatus.CURRENT,
]


def resolve_primary_status(statuses: Sequence[Union[QualityStatus, str]]) -> QualityStatus:
    """
    Select the primary display status from a collection of applicable quality statuses
    using strict deterministic precedence:
    UNAVAILABLE (highest) > INCOMPLETE > STALE > ESTIMATED > CURRENT (lowest).

    If no statuses are provided, defaults to UNAVAILABLE.
    """
    if not statuses:
        return QualityStatus.UNAVAILABLE

    normalized: List[QualityStatus] = []
    for s in statuses:
        if isinstance(s, QualityStatus):
            normalized.append(s)
        elif isinstance(s, str):
            try:
                normalized.append(QualityStatus(s.strip().upper()))
            except ValueError:
                normalized.append(QualityStatus.UNAVAILABLE)

    for p in PRECEDENCE_ORDER:
        if p in normalized:
            return p

    return QualityStatus.UNAVAILABLE


def get_shading_token(status: Union[QualityStatus, str]) -> AtlasShadingToken:
    """Retrieve the authoritative presentation shading token for a quality status."""
    if isinstance(status, str):
        try:
            status = QualityStatus(status.strip().upper())
        except ValueError:
            status = QualityStatus.UNAVAILABLE

    return ATLAS_SHADING_TOKENS.get(status, ATLAS_SHADING_TOKENS[QualityStatus.UNAVAILABLE])
