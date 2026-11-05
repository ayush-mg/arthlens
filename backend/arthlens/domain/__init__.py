"""
ArthLens domain module.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1).
"""

from backend.arthlens.domain.enums import (
    EvidenceFloor,
    EvidenceLevel,
    Kind,
    ResolutionLevel,
    ResolutionTier,
)
from backend.arthlens.domain.interfaces import (
    DataProvider,
    DemandAllocator,
    ILLMClient,
    Repository,
    RuleNode,
    RuleVisitor,
    RunState,
    SimulationModel,
    SpecResult,
    Tool,
    VerificationSpecification,
)
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
    canonical_district_id,
    canonical_nation_id,
    canonical_state_id,
    canonical_subdistrict_id,
)
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import (
    ImmutableQuantityError,
    PolicyRuleRepository,
    QuantityNotFoundError,
    QuantityRepository,
    RepositoryError,
    ScenarioRepository,
    UserRepository,
    GeoUnitRepository,
    ConflictingGeoUnitError,
    OrphanedGeoUnitError,
)
from backend.arthlens.domain.simulation import SimulationMetadata

__all__ = [
    "Kind",
    "EvidenceLevel",
    "EvidenceFloor",
    "ResolutionTier",
    "ResolutionLevel",
    "Quantity",
    "SimulationMetadata",
    "DataProvider",
    "DemandAllocator",
    "SimulationModel",
    "RuleNode",
    "RuleVisitor",
    "SpecResult",
    "VerificationSpecification",
    "Tool",
    "ILLMClient",
    "RunState",
    "Repository",
    "RepositoryError",
    "QuantityNotFoundError",
    "ImmutableQuantityError",
    "QuantityRepository",
    "UserRepository",
    "PolicyRuleRepository",
    "ScenarioRepository",
    "GeoUnitRepository",
    "ConflictingGeoUnitError",
    "OrphanedGeoUnitError",
    "GeoUnit",
    "NavigationStatus",
    "GeometryStatus",
    "AnalyticalStatus",
    "canonical_nation_id",
    "canonical_state_id",
    "canonical_district_id",
    "canonical_subdistrict_id",
]
