"""
SQLAlchemy ORM Models for ArthLens Database Schema.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

import uuid
from datetime import date, datetime
from typing import Any, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Double,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from backend.arthlens.infra.database import Base


# ==============================================================================
# 1. Users, Roles, and Permissions (Handbook 9.1)
# ==============================================================================

class UserModel(Base):
    """User accounts and usage quota tracking."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    quota_counters = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    roles = relationship("RoleModel", secondary="user_roles", back_populates="users")


class RoleModel(Base):
    """System and domain roles."""
    __tablename__ = "roles"

    id = Column(Text, primary_key=True)  # ENTREPRENEUR, STEWARD, ADMIN, etc.
    description = Column(Text, nullable=True)

    users = relationship("UserModel", secondary="user_roles", back_populates="roles")


class UserRoleModel(Base):
    """Association table linking users and assigned roles."""
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Text, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


# ==============================================================================
# 2. Data Sources and Versions (Handbook 9.1)
# ==============================================================================

class SourceModel(Base):
    """Registered external and local data sources."""
    __tablename__ = "sources"

    id = Column(Text, primary_key=True)  # e.g., 'src_osm', 'src_rbi'
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    licence_text = Column(Text, nullable=True)
    max_age_days = Column(Integer, nullable=True)
    status = Column(Text, nullable=False, server_default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    versions = relationship("SourceVersionModel", back_populates="source", cascade="all, delete-orphan")


class SourceVersionModel(Base):
    """Specific snapshot versions of a registered data source."""
    __tablename__ = "source_versions"

    id = Column(Text, primary_key=True)
    source_id = Column(Text, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Text, nullable=False)
    retrieval_date = Column(Date, nullable=False)
    content_hash = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    status = Column(Text, nullable=False, server_default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source = relationship("SourceModel", back_populates="versions")


# ==============================================================================
# 3. Geographic Hierarchy and Facilities (Handbook 9.1)
# ==============================================================================

class GeoUnitModel(Base):
    """Geographic admin boundaries and entities with PostGIS geometries."""
    __tablename__ = "geo_units"

    id = Column(Text, primary_key=True)  # LGD code or hierarchical identifier
    parent_id = Column(Text, ForeignKey("geo_units.id"), nullable=True, index=True)
    level = Column(SmallInteger, nullable=False)  # 0=NATION, 1=STATE, 2=DISTRICT, etc.
    name = Column(Text, nullable=False)
    lgd_code = Column(Text, nullable=True, index=True)
    geometry = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    coverage_status = Column(Text, nullable=False, server_default="FULL")

    __table_args__ = (
        CheckConstraint("level BETWEEN 0 AND 5", name="check_geo_unit_level"),
    )


class FacilityModel(Base):
    """OSM-derived points of interest and competitor facilities."""
    __tablename__ = "facilities"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=True)
    geometry = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)
    category = Column(Text, nullable=False)
    attractiveness_proxy = Column(Double, nullable=True)
    completeness_flag = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ==============================================================================
# 4. Epistemic Ledger (Quantities Table, Handbook 9.1, 9.2)
# ==============================================================================

class QuantityModel(Base):
    """
    Epistemic ledger quantity record with immutable lineage semantics.
    Handbook 9.2 SQL reference definition.
    """
    __tablename__ = "quantities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_key = Column(Text, nullable=False, index=True)
    value = Column(Double, nullable=True)
    unit = Column(Text, nullable=False)
    kind = Column(Text, nullable=False)
    evidence_floor = Column(SmallInteger, nullable=False)
    geo_unit_id = Column(Text, nullable=False, index=True)
    resolution = Column(SmallInteger, nullable=False)
    as_of = Column(Date, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    uncertainty = Column(JSONB, nullable=False)
    source_refs = Column(JSONB, nullable=False, server_default="[]")
    method_id = Column(Text, nullable=False)
    model_version = Column(Text, nullable=False)
    parent_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=False, server_default="{}")
    quality_flags = Column(ARRAY(Text), nullable=False, server_default="{}")
    license_meta = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    simulation_meta = Column(JSONB, nullable=True)  # Dedicated field for P1-4 SimulationMetadata
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "kind IN ('OBSERVED','POLICY_RULE','USER_ASSUMED','ESTIMATED','SCENARIO','CALCULATED','SIMULATED','COMMUNITY_REPORTED')",
            name="check_quantity_kind",
        ),
        CheckConstraint("evidence_floor BETWEEN 1 AND 4", name="check_evidence_floor"),
        CheckConstraint("resolution BETWEEN 0 AND 5", name="check_resolution"),
        Index("quantities_parents_gin", "parent_ids", postgresql_using="gin"),
    )


# ==============================================================================
# 5. Policies and Rules (Handbook 9.1)
# ==============================================================================

class PolicyDocumentModel(Base):
    """Retrieved scheme policy guideline documents."""
    __tablename__ = "policy_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheme_id = Column(Text, nullable=False, index=True)
    document_url = Column(Text, nullable=False)
    sha256 = Column(Text, nullable=False)
    retrieved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(Text, nullable=False, server_default="ACTIVE")


class PolicyRuleModel(Base):
    """Structured AST rules extracted from policy guidelines."""
    __tablename__ = "policy_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("policy_documents.id"), nullable=True)
    scheme_id = Column(Text, nullable=False, index=True)
    version = Column(Text, nullable=False)
    rule_ast = Column(JSONB, nullable=False)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    status = Column(Text, nullable=False, server_default="DRAFT")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','APPROVED','RETIRED')", name="check_policy_rule_status"),
    )


# ==============================================================================
# 6. Business Profiles, Scenarios, and Simulations (Handbook 9.1)
# ==============================================================================

class BusinessProfileModel(Base):
    """User-owned enterprise profile and facts."""
    __tablename__ = "business_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sector_template = Column(Text, nullable=False)
    user_facts = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ScenarioModel(Base):
    """User-owned scenario specifications."""
    __tablename__ = "scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    scenario = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SimulationRunModel(Base):
    """Bit-identical reproducible simulation run results."""
    __tablename__ = "simulation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    seed = Column(Numeric(asdecimal=True), nullable=False)
    model_version = Column(Text, nullable=False)
    git_hash = Column(Text, nullable=True)
    data_version_ids = Column(ARRAY(Text), nullable=False, server_default="{}")
    outputs_references = Column(JSONB, nullable=False, server_default="{}")
    status = Column(Text, nullable=False, server_default="PENDING")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "seed = TRUNC(seed) AND seed >= 0 AND seed <= 18446744073709551615",
            name="check_simulation_run_seed_range",
        ),
    )


# ==============================================================================
# 7. Agent Runs, Steps, and Events (Handbook 9.2)
# ==============================================================================

class AgentRunModel(Base):
    """Orchestrated agent run execution record."""
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    objective = Column(JSONB, nullable=False)
    state = Column(Text, nullable=False)
    steps_used = Column(Integer, nullable=False, server_default="0")
    replans_used = Column(Integer, nullable=False, server_default="0")
    model_calls_used = Column(Integer, nullable=False, server_default="0")
    cost_usd = Column(Numeric(10, 4), nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    steps = relationship("AgentRunStepModel", back_populates="run", cascade="all, delete-orphan")
    events = relationship("RunEventModel", back_populates="run", cascade="all, delete-orphan")


class AgentRunStepModel(Base):
    """Individual execution step with memento checkpoint for resume."""
    __tablename__ = "agent_run_steps"

    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), primary_key=True)
    seq = Column(Integer, primary_key=True)
    tool = Column(Text, nullable=True)
    input = Column(JSONB, nullable=True)
    output = Column(JSONB, nullable=True)
    memento = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    run = relationship("AgentRunModel", back_populates="steps")


class RunEventModel(Base):
    """Sequential events powering UI SSE stream and audit replay."""
    __tablename__ = "run_events"

    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), primary_key=True)
    seq = Column(BigInteger, primary_key=True)
    type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("AgentRunModel", back_populates="events")


# ==============================================================================
# 8. Jobs, Approvals, Follow-up Tasks, and Audit (Handbook 9.1, 9.2)
# ==============================================================================

class JobModel(Base):
    """Async job queue for worker execution."""
    __tablename__ = "jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    kind = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False, server_default="queued", index=True)
    attempts = Column(Integer, nullable=False, server_default="0")
    locked_by = Column(Text, nullable=True)
    run_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class ApprovalModel(Base):
    """Human-in-the-loop approvals for sensitive agent actions."""
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(Text, nullable=False)
    requested_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decided_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decision = Column(Text, nullable=False, server_default="PENDING")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)


class TaskModel(Base):
    """Follow-up tasks identified by verifier gaps."""
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    linked_gap_quantity_id = Column(UUID(as_uuid=True), ForeignKey("quantities.id"), nullable=True)
    status = Column(Text, nullable=False, server_default="OPEN")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuditEventModel(Base):
    """Append-only audit trail for sensitive administrative operations."""
    __tablename__ = "audit_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor = Column(UUID(as_uuid=True), nullable=True)
    action = Column(Text, nullable=False)
    target = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, server_default="{}")
    prev_hash = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class RevokedTokenModel(Base):
    """Revoked JWT IDs (session invalidation upon logout)."""
    __tablename__ = "revoked_tokens"

    jti = Column(Text, primary_key=True)
    revoked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


class RateLimitModel(Base):
    """Concurrency-safe distributed rate limit buckets."""
    __tablename__ = "rate_limits"

    key = Column(Text, primary_key=True)
    count = Column(Integer, nullable=False, server_default="1")
    reset_at = Column(DateTime(timezone=True), nullable=False, index=True)
