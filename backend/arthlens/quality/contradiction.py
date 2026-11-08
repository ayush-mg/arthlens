"""
Authoritative Contradiction Detection Engine for ArthLens Epistemic Ledger (Handbook V5).

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 4.4, 4.5, 4.7, Part 7.4).
Phase: Phase 2 (P2-3 Data Quality and P2-4 Provenance & Verification).

Handbook V5 Invariant:
If two sources disagree beyond tolerance on the same definition, geographic unit,
and temporal period, BOTH remain visible and the claim is marked disputed
until an explicit reconciliation or resolution method is applied.

Requirements:
1. Match quantities using definition_key.
2. Match canonical geographic identity (geo_unit_id).
3. Match compatible temporal support (same as_of / overlapping period).
4. Compare actual uncertainty / tolerance intervals.
5. Use an explicitly registered metric-specific tolerance policy.
6. Do not invent an arbitrary universal percentage.
7. Preserve all conflicting quantities and their provenance.
8. Mark disputed results explicitly (quality flag: CONTRADICTED / DISPUTED).
9. Never silently average or discard conflicting evidence.
10. Do not select the latest value and hide the conflicting source.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

from backend.arthlens.domain.quantity import Quantity


@dataclass(frozen=True)
class MetricTolerancePolicy:
    """Registered tolerance policy for a specific semantic definition key."""

    definition_key: str
    relative_tolerance: float
    absolute_tolerance: Optional[float] = None
    description: str = ""


# No tolerance policy is activated without reviewed source-backed evidence.  In
# its absence, V5 compares explicit uncertainty intervals or exact points;
# callers may register a policy after steward review.
DEFAULT_METRIC_TOLERANCES: Dict[str, MetricTolerancePolicy] = {}


class ContradictionRegistry:
    """Registry managing registered metric tolerance policies."""

    _policies: Dict[str, MetricTolerancePolicy] = dict(DEFAULT_METRIC_TOLERANCES)

    @classmethod
    def get_policy(cls, definition_key: str) -> Optional[MetricTolerancePolicy]:
        """Return registered metric tolerance policy or None if unconfigured."""
        return cls._policies.get(definition_key)

    @classmethod
    def register_policy(cls, policy: MetricTolerancePolicy) -> None:
        """Register or override a metric tolerance policy."""
        cls._policies[policy.definition_key] = policy

    @classmethod
    def reset_defaults(cls) -> None:
        """Reset registry to default policies."""
        cls._policies = dict(DEFAULT_METRIC_TOLERANCES)


def extract_uncertainty_interval(
    q: Quantity, policy: Optional[MetricTolerancePolicy] = None
) -> Tuple[float, float]:
    """
    Extract the effective interval [lower, upper] for a Quantity.
    If explicit ('INTERVAL', lo, hi) is present, use it directly.
    Otherwise apply metric-specific registered tolerance to the scalar value.
    """
    if q.value is None:
        return (0.0, 0.0)

    val = float(q.value)
    unc = q.uncertainty

    # 1. Explicit INTERVAL uncertainty: ('INTERVAL', lo, hi)
    if isinstance(unc, (tuple, list)) and len(unc) == 3 and unc[0] == "INTERVAL":
        try:
            return (float(unc[1]), float(unc[2]))
        except ValueError, TypeError:
            pass

    # 2. Metric-specific tolerance policy
    if policy is not None:
        rel_tol = policy.relative_tolerance
        abs_tol = policy.absolute_tolerance or (abs(val) * rel_tol)
        delta = max(abs(val) * rel_tol, abs_tol)
        return (val - delta, val + delta)

    # 3. Unconfigured metric policy: EXACT point interval (no arbitrary tolerance invented)
    return (val, val)


def periods_are_compatible(as_of_a: Optional[str], as_of_b: Optional[str]) -> bool:
    """
    Check if two observation temporal anchors refer to the same period.
    Two observations from different years/dates (e.g. 2011 vs 2026) are not contradicting;
    they are distinct temporal snapshots.
    """
    if not as_of_a or not as_of_b:
        return False
    # Exact date match
    if str(as_of_a).strip() == str(as_of_b).strip():
        return True
    # Year-level compatibility if either is just YYYY
    str_a = str(as_of_a).strip()[:4]
    str_b = str(as_of_b).strip()[:4]
    return str_a == str_b


def intervals_overlap(interval_a: Tuple[float, float], interval_b: Tuple[float, float]) -> bool:
    """Check if two numeric intervals [lo, hi] overlap."""
    lo_a, hi_a = min(interval_a), max(interval_a)
    lo_b, hi_b = min(interval_b), max(interval_b)
    return max(lo_a, lo_b) <= min(hi_a, hi_b)


@dataclass(frozen=True)
class ContradictionRecord:
    """Detailed record of an epistemic contradiction detected between two quantities."""

    definition_key: str
    geo_unit_id: str
    temporal_period: str
    quantity_id_a: str
    value_a: float
    source_a: str
    quantity_id_b: str
    value_b: float
    source_b: str
    interval_a: Tuple[float, float]
    interval_b: Tuple[float, float]
    discrepancy: float
    relative_discrepancy: float
    policy_description: str


def detect_contradictions(
    quantities: Sequence[Quantity],
) -> Tuple[Set[str], List[ContradictionRecord]]:
    """
    Detect epistemic contradictions across a collection of quantities adhering to Handbook V5.

    Returns:
        contradicted_quantity_ids: Set of Quantity IDs participating in contradictions.
        contradiction_records: List of structured ContradictionRecord audit entries.
    """
    contradicted_ids: Set[str] = set()
    records: List[ContradictionRecord] = []

    # Group quantities by definition_key and geo_unit_id
    grouped: Dict[Tuple[str, str], List[Quantity]] = {}
    for q in quantities:
        if q.value is None:
            continue
        grouped.setdefault((q.definition_key, q.geo_unit_id), []).append(q)

    for (def_key, geo_id), q_list in grouped.items():
        if len(q_list) < 2:
            continue

        policy = ContradictionRegistry.get_policy(def_key)

        # Pairwise comparison
        n = len(q_list)
        for i in range(n):
            for j in range(i + 1, n):
                q1 = q_list[i]
                q2 = q_list[j]

                # Match compatible temporal support
                if not periods_are_compatible(q1.as_of, q2.as_of):
                    continue

                # Different sources required for an empirical contradiction
                src1 = str(q1.source_refs or "")
                src2 = str(q2.source_refs or "")
                if src1 == src2:
                    continue

                # Compare uncertainty/tolerance intervals
                int1 = extract_uncertainty_interval(q1, policy)
                int2 = extract_uncertainty_interval(q2, policy)

                if not intervals_overlap(int1, int2):
                    # Numeric contradiction detected!
                    contradicted_ids.add(str(q1.id))
                    contradicted_ids.add(str(q2.id))

                    denom = max(abs(q1.value), abs(q2.value), 1e-9)
                    discrepancy = abs(q1.value - q2.value)
                    rel_discrepancy = discrepancy / denom

                    records.append(
                        ContradictionRecord(
                            definition_key=def_key,
                            geo_unit_id=geo_id,
                            temporal_period=str(q1.as_of),
                            quantity_id_a=str(q1.id),
                            value_a=q1.value,
                            source_a=src1,
                            quantity_id_b=str(q2.id),
                            value_b=q2.value,
                            source_b=src2,
                            interval_a=int1,
                            interval_b=int2,
                            discrepancy=discrepancy,
                            relative_discrepancy=rel_discrepancy,
                            policy_description=policy.description
                            if policy
                            else "Unconfigured metric policy: zero-tolerance point intervals.",
                        )
                    )

    return contradicted_ids, records
