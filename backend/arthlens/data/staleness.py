"""
Staleness detection and quality flag assignment based on configured source age.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.4, 4.7, Part 7.4).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).
"""

from backend.arthlens.ledger.staleness import (
    apply_staleness_flag,
    is_source_stale,
    parse_as_of_date,
    with_staleness_flag,
)
from backend.arthlens.quality.freshness import (
    FreshnessEvaluation,
    evaluate_staleness,
    get_source_max_age_days,
)

__all__ = [
    "apply_staleness_flag",
    "is_source_stale",
    "parse_as_of_date",
    "with_staleness_flag",
    "evaluate_staleness",
    "get_source_max_age_days",
    "FreshnessEvaluation",
]

