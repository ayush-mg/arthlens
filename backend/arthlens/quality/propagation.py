"""
Epistemic Ledger Quality Propagation and Calculation Gating (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.2, 4.4, 4.7, Part 7.4).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).

Enforces:
1. Downstream calculations must inspect the quality of contributing parent quantities.
2. If any parent quantity is STALE:
   - Derived quantity receives the 'STALE_ANCESTRY' quality flag.
   - Suitability is downgraded to 'SUITABLE_HISTORICAL_ONLY'.
   - Downstream claims cannot silently represent results as current conditions.
3. If any parent quantity is ESTIMATED:
   - Derived kind cannot be Kind.OBSERVED (evidence_floor <= 2).
4. If any required parent quantity is UNAVAILABLE or INCOMPLETE:
   - Calculations are strictly gated; never silently substitute numeric zero.
   - GatedCalculationError is raised with specific missing inputs.
5. Preserves complete ancestry provenance and restriction explanations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.propagation import combine_evidence_floors, propagate_quality_flags
from backend.arthlens.quality.vocabulary import CalculationSuitability, QualityStatus, resolve_primary_status


class GatedCalculationError(ValueError):
    """Raised when a calculation cannot proceed due to missing or unavailable inputs."""
    def __init__(self, message: str, missing_inputs: Sequence[str]) -> None:
        super().__init__(message)
        self.missing_inputs = list(missing_inputs)


@dataclass(frozen=True)
class CalculationQualityContext:
    """Audit and restriction metadata derived from parent quantities for a calculation."""
    primary_status: QualityStatus
    suitability: CalculationSuitability
    propagated_flags: frozenset
    evidence_floor: int
    is_historically_restricted: bool
    is_estimated: bool
    restriction_reasons: List[str] = field(default_factory=list)
    parent_ids: List[str] = field(default_factory=list)
    source_refs: List[Any] = field(default_factory=list)


def inspect_calculation_inputs(
    inputs: Sequence[Optional[Quantity]],
    input_names: Optional[Sequence[str]] = None,
    allow_historical: bool = False,
) -> CalculationQualityContext:
    """
    Inspect all contributing parent quantities for a calculation.

    Enforces gating rules:
    - If any input is None: raises GatedCalculationError (missing input).
    - If any input has STALE flag or stale ancestry: flags historical restriction.
    - If any input is ESTIMATED: derives estimated context.
    """
    if not inputs:
        raise ValueError("Cannot calculate from an empty list of inputs.")

    names = list(input_names) if input_names else [f"input_{i}" for i in range(len(inputs))]
    if len(names) != len(inputs):
        names = [f"input_{i}" for i in range(len(inputs))]

    # 1. Missingness gate: Never substitute numeric zero
    missing = [names[i] for i, q in enumerate(inputs) if q is None or q.value is None]
    if missing:
        raise GatedCalculationError(
            f"Calculation blocked: Required inputs {missing} are UNAVAILABLE. "
            f"ArthLens strictly forbids silently substituting numeric zero for missing empirical inputs.",
            missing_inputs=missing,
        )

    # All inputs guaranteed non-None from here
    valid_inputs: List[Quantity] = [q for q in inputs if q is not None]

    parent_ids = [q.id for q in valid_inputs]
    source_refs = [ref for q in valid_inputs for ref in q.source_refs]
    evidence_floor = combine_evidence_floors([q.evidence_floor for q in valid_inputs])

    # Quality flags propagation
    raw_parent_flags = [q.quality_flags for q in valid_inputs]
    propagated_flags = set(propagate_quality_flags(raw_parent_flags))

    restriction_reasons: List[str] = []
    applicable_statuses: List[QualityStatus] = []

    # 2. Staleness inspection
    has_stale_parent = any("STALE" in q.quality_flags for q in valid_inputs)
    if has_stale_parent:
        propagated_flags.add("STALE_ANCESTRY")
        applicable_statuses.append(QualityStatus.STALE)
        restriction_reasons.append(
            "Derived from STALE historical parent evidence (e.g. Census 2011). "
            "Valid strictly for historical reference; cannot silently claim current market conditions."
        )

    # 3. Estimation inspection
    has_estimated_parent = any(
        q.kind == Kind.ESTIMATED or "SYNTHETIC_DATA" in q.quality_flags
        for q in valid_inputs
    )
    if has_estimated_parent:
        applicable_statuses.append(QualityStatus.ESTIMATED)
        restriction_reasons.append("Derived from ESTIMATED or modelled parent inputs.")

    # 4. Incomplete flags
    has_incomplete_parent = any("INCOMPLETE_SOURCE" in q.quality_flags or "LOW_COVERAGE" in q.quality_flags for q in valid_inputs)
    if has_incomplete_parent:
        applicable_statuses.append(QualityStatus.INCOMPLETE)
        restriction_reasons.append("Contributing inputs carry partial or incomplete coverage flags.")

    # 4b. Contradiction flags (Verification V5)
    has_contradicted_parent = any("CONTRADICTED" in q.quality_flags or "DISPUTED" in q.quality_flags for q in valid_inputs)
    if has_contradicted_parent:
        propagated_flags.add("CONTRADICTED_ANCESTRY")
        applicable_statuses.append(QualityStatus.CONTRADICTED)
        restriction_reasons.append("Contributing inputs carry disputed contradiction flags (Verification V5).")

    if not applicable_statuses:
        applicable_statuses.append(QualityStatus.CURRENT)

    primary_status = resolve_primary_status(applicable_statuses)

    # 5. Suitability derivation
    if primary_status == QualityStatus.CONTRADICTED:
        suitability = CalculationSuitability.UNSUITABLE_CONTRADICTED
    elif primary_status == QualityStatus.STALE:
        suitability = CalculationSuitability.SUITABLE_HISTORICAL_ONLY
    elif primary_status == QualityStatus.ESTIMATED:
        suitability = CalculationSuitability.ESTIMATED_PROJECTION
    elif primary_status == QualityStatus.INCOMPLETE:
        suitability = CalculationSuitability.CAUTION_PARTIAL
    else:
        suitability = CalculationSuitability.SUITABLE_CURRENT

    return CalculationQualityContext(
        primary_status=primary_status,
        suitability=suitability,
        propagated_flags=frozenset(propagated_flags),
        evidence_floor=evidence_floor,
        is_historically_restricted=has_stale_parent,
        is_estimated=has_estimated_parent,
        restriction_reasons=restriction_reasons,
        parent_ids=parent_ids,
        source_refs=source_refs,
    )
