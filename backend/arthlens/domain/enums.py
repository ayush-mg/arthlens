"""
Domain Enumerations for ArthLens.

Authoritative Specification: ArthLens Build Handbook v1.0 (Parts 4.1, 4.2, 4.3, 5.1).
Phase: P1-2 (Domain Classes, Enums, and Interfaces).
"""

from enum import Enum, IntEnum


class Kind(str, Enum):
    """
    Epistemic kind of a ledger quantity.

    Handbook Reference: Section 4.1, 5.1.
    Values:
        OBSERVED: Empirically measured in the real world (e.g., census counts, survey tables).
        POLICY_RULE: Extracted directly from official government scheme guidelines.
        USER_ASSUMED: Explicitly input or assumed by the user for their business.
        ESTIMATED: Derived via a registered statistical/spatial estimation method (e.g., popweight_v1).
        SCENARIO: Hypothetical scenario parameter or stress-test prior.
        CALCULATED: Deterministically calculated from parent quantities.
        SIMULATED: Generated via Monte Carlo or stochastic simulation runs.
    """
    OBSERVED = "OBSERVED"
    POLICY_RULE = "POLICY_RULE"
    USER_ASSUMED = "USER_ASSUMED"
    ESTIMATED = "ESTIMATED"
    SCENARIO = "SCENARIO"
    CALCULATED = "CALCULATED"
    SIMULATED = "SIMULATED"


class EvidenceLevel(IntEnum):
    """
    Evidence floor strength rank for base quantity classes.

    Handbook Reference: Section 4.2:
        Base classes ranked by strength (higher is stronger):
        OBSERVED = POLICY_RULE (4) > USER_ASSUMED (3) > ESTIMATED (2) > SCENARIO (1).
    """
    SCENARIO = 1
    ESTIMATED = 2
    USER_ASSUMED = 3
    POLICY_RULE = 4
    OBSERVED = 4


# Alias for EvidenceLevel per Handbook Section 4.1 field 5 ("evidence_floor")
EvidenceFloor = EvidenceLevel


class ResolutionTier(IntEnum):
    """
    Geographic resolution hierarchy levels ordered from coarse (0) to fine (5).

    Handbook Reference: Section 4.3:
        Order from coarse to fine:
        NATION(0) < STATE(1) < DISTRICT(2) < SUBDISTRICT(3) < VILLAGE_URBAN(4) < POINT(5).
    """
    NATION = 0
    STATE = 1
    DISTRICT = 2
    SUBDISTRICT = 3
    VILLAGE_URBAN = 4
    POINT = 5


# Alias for ResolutionTier per Handbook Section 4.3
ResolutionLevel = ResolutionTier
