"""
ArthLens Epistemic Ledger package.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4, 5.1).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).
"""

from backend.arthlens.ledger.downscaling import DownscalingRegistry, downscale
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.propagation import (
    combine_evidence_floors,
    combine_resolutions,
    propagate_quality_flags,
)
from backend.arthlens.ledger.renderer import (
    AllowlistConfig,
    RenderResult,
    ReportRenderer,
)
from backend.arthlens.ledger.specs import (
    AndSpecification,
    ContradictionVisibilitySpec,
    DerivationDowngradeSpec,
    GeographicPrecisionSpec,
    MissingAssumptionSpec,
    PolicyCitationSpec,
    ReproducibilitySpec,
    SimulationMetadata,
    SimulationModelVersionSpec,
    SourceAttributionSpec,
    SpecResult,
    UnitCompatibilitySpec,
    VerificationSpecification,
)
from backend.arthlens.ledger.staleness import (
    apply_staleness_flag,
    is_source_stale,
    parse_as_of_date,
    with_staleness_flag,
)
from backend.arthlens.ledger.uncertainty import combine_uncertainty
from backend.arthlens.ledger.units import (
    check_unit_compatibility,
    get_unit_registry,
)
from backend.arthlens.ledger.verifier import (
    LedgerVerifier,
    VerificationReport,
)

__all__ = [
    "Ledger",
    "DownscalingRegistry",
    "downscale",
    "combine_evidence_floors",
    "combine_resolutions",
    "propagate_quality_flags",
    "combine_uncertainty",
    "check_unit_compatibility",
    "get_unit_registry",
    "is_source_stale",
    "parse_as_of_date",
    "apply_staleness_flag",
    "with_staleness_flag",
    "VerificationSpecification",
    "SpecResult",
    "AndSpecification",
    "DerivationDowngradeSpec",
    "GeographicPrecisionSpec",
    "PolicyCitationSpec",
    "SourceAttributionSpec",
    "ContradictionVisibilitySpec",
    "UnitCompatibilitySpec",
    "ReproducibilitySpec",
    "MissingAssumptionSpec",
    "SimulationMetadata",
    "SimulationModelVersionSpec",
    "LedgerVerifier",
    "VerificationReport",
    "ReportRenderer",
    "AllowlistConfig",
    "RenderResult",
]
