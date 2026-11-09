"""
SQLAlchemy ORM Models for ArthLens Database Schema.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
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
    records = relationship("SourceRecordModel", back_populates="version", cascade="all, delete-orphan")


class SourceRecordModel(Base):
    """Normalized source records preserving raw, normalized, and provenance attributes."""
    __tablename__ = "source_records"

    id = Column(Text, primary_key=True)
    source_id = Column(Text, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    source_version_id = Column(Text, ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    record_id = Column(Text, nullable=False, index=True)
    original_fields = Column(JSONB, nullable=False)
    normalized_fields = Column(JSONB, nullable=False)
    canonical_units = Column(JSONB, nullable=False)
    geo_resolved = Column(Boolean, nullable=False, server_default="false")
    geo_unit_id = Column(Text, nullable=True, index=True)
    unresolved_raw_id = Column(Text, nullable=True)
    resolution_tier = Column(SmallInteger, nullable=True)
    as_of = Column(Date, nullable=True)
    temporal_support = Column(JSONB, nullable=True)
    license_name = Column(Text, nullable=True)
    attribution = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    version = relationship("SourceVersionModel", back_populates="records")

    __table_args__ = (
        UniqueConstraint("source_version_id", "record_id", name="uq_source_records_version_record"),
    )


# ==============================================================================
# 3. Geographic Hierarchy and Facilities (Handbook 9.1)
# ==============================================================================

class GeoUnitModel(Base):
    """Geographic admin boundaries and entities with PostGIS geometries."""
    __tablename__ = "geo_units"

    id = Column(Text, primary_key=True)  # e.g., 'in', 'in:state:09', 'in:district:175'
    parent_id = Column(Text, ForeignKey("geo_units.id"), nullable=True, index=True)
    level = Column(SmallInteger, nullable=False)  # 0=NATION, 1=STATE, 2=DISTRICT, 3=SUBDISTRICT, etc.
    name = Column(Text, nullable=False)
    lgd_code = Column(Text, nullable=True, index=True)
    geometry = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
    coverage_status = Column(Text, nullable=False, server_default="NAVIGABLE")
    geometry_status = Column(Text, nullable=False, server_default="GEOMETRY_MISSING")
    analytical_status = Column(Text, nullable=False, server_default="ANALYSIS_UNAVAILABLE")
    census_code = Column(Text, nullable=True)
    geometry_source_record_id = Column(Text, ForeignKey("source_records.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint("level BETWEEN 0 AND 5", name="check_geo_unit_level"),
        CheckConstraint(
            "coverage_status IN ('NAVIGABLE', 'HIERARCHY_UNRESOLVED')",
            name="check_geo_unit_coverage_status",
        ),
        CheckConstraint(
            "geometry_status IN ('GEOMETRY_VERIFIED', 'GEOMETRY_SIMPLIFIED', 'GEOMETRY_HISTORICAL', 'GEOMETRY_UNVALIDATED', 'GEOMETRY_MISSING')",
            name="check_geo_unit_geometry_status",
        ),
        CheckConstraint(
            "analytical_status IN ('ANALYSABLE', 'ANALYSIS_UNAVAILABLE')",
            name="check_geo_unit_analytical_status",
        ),
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


class RoadNodeModel(Base):
    """OSM road node with exact source-record provenance."""
    __tablename__ = "road_nodes"

    id = Column(Text, primary_key=True)
    source_version_id = Column(
        Text,
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    osm_node_id = Column(Text, nullable=False)
    geometry = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False)
    source_record_id = Column(
        Text,
        ForeignKey("source_records.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("source_version_id", "osm_node_id", name="uq_road_nodes_version_osm_node"),
        Index("ix_road_nodes_geometry_gist", "geometry", postgresql_using="gist"),
    )


class RoadEdgeModel(Base):
    """Directed OSM road segment indexed for site-local PostGIS extraction."""
    __tablename__ = "road_edges"

    id = Column(Text, primary_key=True)
    source_version_id = Column(
        Text,
        ForeignKey("source_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    osm_way_id = Column(Text, nullable=False)
    segment_index = Column(Integer, nullable=False)
    direction = Column(Text, nullable=False)
    from_node_id = Column(Text, ForeignKey("road_nodes.id", ondelete="CASCADE"), nullable=False)
    to_node_id = Column(Text, ForeignKey("road_nodes.id", ondelete="CASCADE"), nullable=False)
    length_m = Column(Double, nullable=False)
    road_class = Column(Text, nullable=False)
    geometry = Column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False)
    source_record_id = Column(
        Text,
        ForeignKey("source_records.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_version_id",
            "osm_way_id",
            "segment_index",
            "direction",
            name="uq_road_edges_version_way_segment_direction",
        ),
        CheckConstraint("length_m > 0", name="check_road_edges_positive_length"),
        CheckConstraint("direction IN ('forward', 'reverse')", name="check_road_edges_direction"),
        Index("ix_road_edges_source_nodes", "source_version_id", "from_node_id"),
        Index("ix_road_edges_geometry_gist", "geometry", postgresql_using="gist"),
    )


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
    """Exact registered source snapshots reviewed for policy-rule use."""
    __tablename__ = "policy_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scheme_id = Column(Text, nullable=False, index=True)
    document_url = Column(Text, nullable=False)
    sha256 = Column(Text, nullable=False)
    source_version_id = Column(
        Text,
        ForeignKey("source_versions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    retrieved_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(Text, nullable=False, server_default="PENDING_REVIEW")
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    review_note = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING_REVIEW','VERIFIED','REJECTED')",
            name="check_policy_document_status",
        ),
    )


class PolicyRuleModel(Base):
    """Structured AST rules extracted from policy guidelines."""
    __tablename__ = "policy_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("policy_documents.id"), nullable=True)
    scheme_id = Column(Text, nullable=False, index=True)
    rule_key = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    rule_ast = Column(JSONB, nullable=False)
    evidence_requirements = Column(JSONB, nullable=False, server_default="{}")
    source_references = Column(JSONB, nullable=False, server_default="[]")
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    status = Column(Text, nullable=False, server_default="DRAFT")
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_note = Column(Text, nullable=True)
    retired_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)
    retirement_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','APPROVED','RETIRED')", name="check_policy_rule_status"),
        UniqueConstraint("scheme_id", "rule_key", "version", name="uq_policy_scheme_rule_version"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="check_policy_effective_period",
        ),
    )


class PolicyEvaluationModel(Base):
    """Append-only source-versioned result and evidence trace for a policy assessment."""

    __tablename__ = "policy_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scheme_id = Column(Text, nullable=False, index=True)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("policy_rules.id", ondelete="SET NULL"), nullable=True)
    rule_key = Column(Text, nullable=False)
    rule_version = Column(Text, nullable=True)
    as_of = Column(Date, nullable=False)
    outcome = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    fact_quantity_ids = Column(JSONB, nullable=False, server_default="{}")
    trace = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("outcome IN ('TRUE','FALSE','UNKNOWN')", name="check_policy_evaluation_outcome"),
        CheckConstraint(
            "status IN ('RULE_UNAVAILABLE','INSUFFICIENT_DATA','SCENARIO_ONLY','ASSESSED')",
            name="check_policy_evaluation_status",
        ),
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


class ScenarioComparisonModel(Base):
    """Immutable owner-scoped comparison between two saved scenario result snapshots."""
    __tablename__ = "scenario_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    left_scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    right_scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Text, nullable=False)
    metric_results = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("left_scenario_id <> right_scenario_id", name="check_scenario_comparison_distinct_scenarios"),
        CheckConstraint("status IN ('COMPLETED','PARTIAL','INSUFFICIENT_DATA')", name="check_scenario_comparison_status"),
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
    claimed_by = Column(Text, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    recovery_attempts = Column(Integer, nullable=False, server_default="0")
    max_recovery_attempts = Column(Integer, nullable=False, server_default="3")
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
    priority = Column(Text, nullable=False, server_default="MEDIUM")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
            name="check_task_status",
        ),
        CheckConstraint(
            "priority IN ('HIGH', 'MEDIUM', 'LOW')",
            name="check_task_priority",
        ),
    )


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
