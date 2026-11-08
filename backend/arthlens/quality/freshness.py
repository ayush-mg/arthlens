"""
Freshness Policy, Date Tracking, and Injected Clock Staleness Evaluation (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.4, 4.7, Part 7.1, 7.5 Step 10).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).

Maintains strict separation across:
1. as_of: Observation date / ground truth period.
2. publication_date: Date the publisher released the dataset snapshot.
3. retrieval_date: Date ArthLens fetched or downloaded the file.
4. ingestion_date: Date the snapshot was parsed and stored in the database.
5. evaluation_date: Date staleness is assessed (supports injected clocks).

Critical Invariant:
A recent retrieval or download date (e.g. November 2026) NEVER makes historical observations
(e.g. Census 2011 as_of 2011-03-01) appear fresh or current.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Optional, Union

from backend.arthlens.ledger.staleness import parse_as_of_date


@dataclass(frozen=True)
class FreshnessPolicy:
    """
    Approved freshness threshold policy for an authoritative data source.
    Handbook Reference: Section 4.4, Part 7.1.
    """
    source_id: str
    source_name: str
    max_age_days: int
    ten_year_rule: bool = False
    description: str = ""


# Default approved freshness policies from authoritative source registers (Handbook Part 7.1, 7.4)
# Note: Only Census demographic counts (DS-05 / DS-05-PCA) have an approved 3,650-day (10-year) staleness policy.
# DS-04 (180 days), DS-08 (365 days), and DS-09 (1825 days) lack source-level approval in their registers
# and are strictly maintained as unconfigured to prevent inventing unverified freshness claims.
DEFAULT_FRESHNESS_POLICIES: Dict[str, FreshnessPolicy] = {
    "DS-05": FreshnessPolicy(
        source_id="DS-05",
        source_name="Census 2011 Primary Census Abstract",
        max_age_days=3650,  # 10 years (Handbook Part 7.4)
        ten_year_rule=True,
        description="Official Census of India 2011 demographic counts; subject to the strict 10-year staleness rule.",
    ),
    "DS-05-PCA": FreshnessPolicy(
        source_id="DS-05-PCA",
        source_name="Census 2011 Primary Census Abstract (Demographic Counts)",
        max_age_days=3650,  # 10 years (Handbook Part 7.4)
        ten_year_rule=True,
        description="Official Census of India 2011 demographic counts; subject to the strict 10-year staleness rule.",
    ),
}


class FreshnessRegistry:
    """Registry managing approved source freshness policies."""

    _policies: Dict[str, FreshnessPolicy] = dict(DEFAULT_FRESHNESS_POLICIES)

    @classmethod
    def get_policy(cls, source_id: Optional[Any]) -> Optional[FreshnessPolicy]:
        """
        Return the approved freshness policy for a source.
        Returns None if source_id is missing or unconfigured (does NOT guess or invent defaults).
        Handles string, tuple/list source_refs, and version-prefixed identifiers (e.g. 'DS-05:55a4...').
        """
        if not source_id:
            return None
        if isinstance(source_id, (tuple, list)):
            source_id = source_id[0] if source_id else None
        if not isinstance(source_id, str):
            return None
        clean_id = source_id.split(":")[0].strip().upper()
        return cls._policies.get(clean_id)

    @classmethod
    def register_policy(cls, policy: FreshnessPolicy) -> None:
        """Register or override an approved freshness policy."""
        cls._policies[policy.source_id.strip().upper()] = policy

    @classmethod
    def reset_defaults(cls) -> None:
        """Reset registry to default approved policies."""
        cls._policies = dict(DEFAULT_FRESHNESS_POLICIES)


@dataclass(frozen=True)
class FreshnessEvaluation:
    """Result of an evaluation of an indicator or source observation date."""
    is_stale: bool
    as_of_date: Optional[date]
    evaluation_date: date
    elapsed_days: Optional[int]
    max_age_days: Optional[int]
    has_policy: bool
    explanation: str
    retrieval_date: Optional[date] = None
    publication_date: Optional[date] = None


def evaluate_staleness(
    as_of: Optional[Union[str, date, datetime]],
    source_id: Optional[str] = None,
    custom_max_age_days: Optional[int] = None,
    evaluation_date: Optional[Union[str, date, datetime]] = None,
    retrieval_date: Optional[Union[str, date, datetime]] = None,
    publication_date: Optional[Union[str, date, datetime]] = None,
) -> FreshnessEvaluation:
    """
    Deterministically evaluate staleness of an observation using an injected evaluation clock.

    Critical Invariant:
    A recent retrieval_date (download time) does NOT make historical observations current.
    Staleness is measured strictly between as_of (observation period) and evaluation_date.

    Args:
        as_of: Ground-truth observation date of the data.
        source_id: Registered source identifier (e.g. 'DS-05').
        custom_max_age_days: Explicit override for max allowed age in days.
        evaluation_date: Injected evaluation clock (defaults to date.today()).
        retrieval_date: Timestamp when file was downloaded (for provenance tracking only).
        publication_date: Timestamp when publisher issued the data.

    Returns:
        FreshnessEvaluation containing staleness flag, elapsed days, and detailed audit explanation.
    """
    eval_d = parse_as_of_date(evaluation_date) if evaluation_date is not None else date.today()
    ret_d = parse_as_of_date(retrieval_date) if retrieval_date is not None else None
    pub_d = parse_as_of_date(publication_date) if publication_date is not None else None

    # Handle missing observation date
    if not as_of:
        return FreshnessEvaluation(
            is_stale=False,
            as_of_date=None,
            evaluation_date=eval_d,
            elapsed_days=None,
            max_age_days=None,
            has_policy=False,
            explanation="Observation date (as_of) is missing; freshness cannot be verified.",
            retrieval_date=ret_d,
            publication_date=pub_d,
        )

    try:
        as_of_d = parse_as_of_date(as_of)
    except Exception as e:
        return FreshnessEvaluation(
            is_stale=False,
            as_of_date=None,
            evaluation_date=eval_d,
            elapsed_days=None,
            max_age_days=None,
            has_policy=False,
            explanation=f"Invalid observation date format '{as_of}': {e}",
            retrieval_date=ret_d,
            publication_date=pub_d,
        )

    elapsed = (eval_d - as_of_d).days

    # Determine maximum allowed age
    max_days: Optional[int] = None
    policy = FreshnessRegistry.get_policy(source_id)

    if custom_max_age_days is not None:
        if custom_max_age_days < 0:
            raise ValueError(f"custom_max_age_days must be non-negative, got {custom_max_age_days}")
        max_days = custom_max_age_days
        has_policy = True
    elif policy is not None:
        max_days = policy.max_age_days
        has_policy = True
    else:
        # Unknown source lacking an approved policy: do NOT invent arbitrary threshold!
        return FreshnessEvaluation(
            is_stale=False,
            as_of_date=as_of_d,
            evaluation_date=eval_d,
            elapsed_days=elapsed,
            max_age_days=None,
            has_policy=False,
            explanation=(
                f"Source '{source_id}' lacks an approved freshness policy. "
                f"Elapsed time is {elapsed} days ({as_of_d.isoformat()} to {eval_d.isoformat()}), "
                f"but freshness remains unverified without an established threshold."
            ),
            retrieval_date=ret_d,
            publication_date=pub_d,
        )

    # Staleness check: elapsed strictly greater than max_days
    is_stale = elapsed > max_days

    if is_stale:
        over_by = elapsed - max_days
        explanation = (
            f"Observation date {as_of_d.isoformat()} is STALE: elapsed {elapsed} days exceeds "
            f"maximum threshold of {max_days} days by {over_by} days as of evaluation date {eval_d.isoformat()}."
        )
        if policy and policy.ten_year_rule:
            explanation += " Subject to Handbook ten-year staleness rule; must never represent current population."
    else:
        remaining = max_days - elapsed
        explanation = (
            f"Observation date {as_of_d.isoformat()} is fresh: elapsed {elapsed} days is within "
            f"maximum threshold of {max_days} days ({remaining} days remaining as of {eval_d.isoformat()})."
        )

    return FreshnessEvaluation(
        is_stale=is_stale,
        as_of_date=as_of_d,
        evaluation_date=eval_d,
        elapsed_days=elapsed,
        max_age_days=max_days,
        has_policy=has_policy,
        explanation=explanation,
        retrieval_date=ret_d,
        publication_date=pub_d,
    )
