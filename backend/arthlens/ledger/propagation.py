"""
Evidence floor, geographic resolution, and quality flag propagation rules.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.2, 4.3, 4.4, 4.7).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).
"""

from typing import Optional, Sequence

from backend.arthlens.ledger.downscaling import DownscalingRegistry


def combine_evidence_floors(parent_floors: Sequence[int]) -> int:
    """
    Compute derived evidence floor as the minimum of parent evidence floors.

    Handbook Reference: Section 4.2:
        Base classes ranked by strength:
        OBSERVED = POLICY_RULE (4) > USER_ASSUMED (3) > ESTIMATED (2) > SCENARIO (1).
        A derived quantity (kind CALCULATED or SIMULATED) has evidence_floor = minimum
        evidence_floor of its parents.
    """
    if not parent_floors:
        raise ValueError("Cannot combine evidence floors of an empty parent list.")
    for floor in parent_floors:
        if not (1 <= floor <= 4):
            raise ValueError(f"Parent evidence floor {floor} is out of valid range 1..4.")
    return min(parent_floors)


def combine_resolutions(
    parent_resolutions: Sequence[int],
    downscaling_method: Optional[str] = None,
    target_resolution: Optional[int] = None,
) -> int:
    """
    Compute derived geographic resolution.

    Handbook Reference: Section 4.3:
        Order from coarse to fine:
        NATION(0) < STATE(1) < DISTRICT(2) < SUBDISTRICT(3) < VILLAGE_URBAN(4) < POINT(5).
        A derived quantity's resolution is the coarsest (lowest index) among its parents.
        Exception: a registered downscaling method may produce a finer resolution.
    """
    if not parent_resolutions:
        raise ValueError("Cannot combine resolutions of an empty parent list.")

    coarsest = min(parent_resolutions)

    if downscaling_method is not None:
        if not DownscalingRegistry.is_registered(downscaling_method):
            raise ValueError(f"Unregistered downscaling method: '{downscaling_method}'")
        if target_resolution is not None:
            if not (0 <= target_resolution <= 5):
                raise ValueError(f"target_resolution {target_resolution} must be between 0 and 5.")
            return target_resolution

    return coarsest


def propagate_quality_flags(parent_flags: Sequence[frozenset]) -> frozenset:
    """
    Propagate quality flags (STALE, INCOMPLETE_SOURCE, LOW_COVERAGE, etc.) from parents.

    Handbook Reference: Section 4.1 (field 12), Section 4.4:
        Derived quantities inherit STALE and all quality flags from parents.
    """
    if not parent_flags:
        return frozenset()
    combined = set()
    for flags in parent_flags:
        if flags:
            combined.update(flags)
    return frozenset(combined)
