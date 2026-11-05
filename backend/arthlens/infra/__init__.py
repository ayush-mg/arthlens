"""
Infrastructure module for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

from backend.arthlens.infra.config import get_database_url, get_environment
from backend.arthlens.infra.database import Base, get_db_session, get_engine, get_session_factory
from backend.arthlens.infra.in_memory import (
    InMemoryGeoUnitRepository,
    InMemoryPolicyRuleRepository,
    InMemoryQuantityRepository,
    InMemoryScenarioRepository,
    InMemorySourceRecordRepository,
    InMemorySourceRepository,
    InMemoryUserRepository,
)
from backend.arthlens.infra.models import (
    AgentRunModel,
    AgentRunStepModel,
    ApprovalModel,
    AuditEventModel,
    BusinessProfileModel,
    FacilityModel,
    GeoUnitModel,
    JobModel,
    PolicyDocumentModel,
    PolicyRuleModel,
    QuantityModel,
    RoleModel,
    RunEventModel,
    ScenarioModel,
    SimulationRunModel,
    SourceModel,
    SourceRecordModel,
    SourceVersionModel,
    TaskModel,
    UserModel,
    UserRoleModel,
)
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresPolicyRuleRepository,
    PostgresQuantityRepository,
    PostgresScenarioRepository,
    PostgresSourceRecordRepository,
    PostgresSourceRepository,
    PostgresUserRepository,
)

__all__ = [
    "get_database_url",
    "get_environment",
    "Base",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "UserModel",
    "RoleModel",
    "UserRoleModel",
    "SourceModel",
    "SourceVersionModel",
    "SourceRecordModel",
    "GeoUnitModel",
    "FacilityModel",
    "QuantityModel",
    "PolicyDocumentModel",
    "PolicyRuleModel",
    "BusinessProfileModel",
    "ScenarioModel",
    "SimulationRunModel",
    "AgentRunModel",
    "AgentRunStepModel",
    "RunEventModel",
    "JobModel",
    "ApprovalModel",
    "TaskModel",
    "AuditEventModel",
    "PostgresQuantityRepository",
    "PostgresGeoUnitRepository",
    "PostgresUserRepository",
    "PostgresPolicyRuleRepository",
    "PostgresScenarioRepository",
    "PostgresSourceRepository",
    "PostgresSourceRecordRepository",
    "InMemoryQuantityRepository",
    "InMemoryGeoUnitRepository",
    "InMemoryUserRepository",
    "InMemoryPolicyRuleRepository",
    "InMemoryScenarioRepository",
    "InMemorySourceRepository",
    "InMemorySourceRecordRepository",
]
