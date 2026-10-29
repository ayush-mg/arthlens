"""initial_schema

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-10-29 15:00:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1, 9.2).
Phase: P1-5 (Alembic database migrations).
"""
from typing import Sequence, Union

from alembic import op
import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensure PostGIS extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. Users, roles, user_roles
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("quota_counters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Text(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    # 2. Sources and source_versions
    op.create_table(
        "sources",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("licence_text", sa.Text(), nullable=True),
        sa.Column("max_age_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "source_versions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source_id", sa.Text(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("retrieval_date", sa.Date(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_source_versions_source_id", "source_versions", ["source_id"])

    # 3. Geo units and facilities
    op.create_table(
        "geo_units",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("parent_id", sa.Text(), sa.ForeignKey("geo_units.id"), nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("lgd_code", sa.Text(), nullable=True),
        sa.Column("geometry", geoalchemy2.types.Geometry(geometry_type="GEOMETRY", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"), nullable=True),
        sa.Column("coverage_status", sa.Text(), nullable=False, server_default="FULL"),
        sa.CheckConstraint("level BETWEEN 0 AND 5", name="check_geo_unit_level"),
    )
    op.create_index("ix_geo_units_parent_id", "geo_units", ["parent_id"])
    op.create_index("ix_geo_units_lgd_code", "geo_units", ["lgd_code"])

    op.create_table(
        "facilities",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("geometry", geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("attractiveness_proxy", sa.Double(), nullable=True),
        sa.Column("completeness_flag", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 4. Quantities (Epistemic Ledger)
    op.create_table(
        "quantities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("definition_key", sa.Text(), nullable=False),
        sa.Column("value", sa.Double(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("evidence_floor", sa.SmallInteger(), nullable=False),
        sa.Column("geo_unit_id", sa.Text(), nullable=False),
        sa.Column("resolution", sa.SmallInteger(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("uncertainty", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("method_id", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("parent_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("quality_flags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("license_meta", sa.Text(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("simulation_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "kind IN ('OBSERVED','POLICY_RULE','USER_ASSUMED','ESTIMATED','SCENARIO','CALCULATED','SIMULATED','COMMUNITY_REPORTED')",
            name="check_quantity_kind",
        ),
        sa.CheckConstraint("evidence_floor BETWEEN 1 AND 4", name="check_evidence_floor"),
        sa.CheckConstraint("resolution BETWEEN 0 AND 5", name="check_resolution"),
    )
    op.create_index("ix_quantities_definition_key", "quantities", ["definition_key"])
    op.create_index("ix_quantities_geo_unit_id", "quantities", ["geo_unit_id"])
    op.create_index("quantities_parents_gin", "quantities", ["parent_ids"], postgresql_using="gin")

    # 5. Policies and Rules
    op.create_table(
        "policy_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scheme_id", sa.Text(), nullable=False),
        sa.Column("document_url", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_policy_documents_scheme_id", "policy_documents", ["scheme_id"])

    op.create_table(
        "policy_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policy_documents.id"), nullable=True),
        sa.Column("scheme_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("rule_ast", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('DRAFT','APPROVED','RETIRED')", name="check_policy_rule_status"),
    )
    op.create_index("ix_policy_rules_scheme_id", "policy_rules", ["scheme_id"])

    # 6. Business profiles, scenarios, simulation_runs
    op.create_table(
        "business_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sector_template", sa.Text(), nullable=False),
        sa.Column("user_facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_business_profiles_owner_id", "business_profiles", ["owner_id"])

    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("scenario", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_scenarios_owner_id", "scenarios", ["owner_id"])

    op.create_table(
        "simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("git_hash", sa.Text(), nullable=True),
        sa.Column("data_version_ids", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("outputs_references", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_simulation_runs_scenario_id", "simulation_runs", ["scenario_id"])

    # 7. Agent runs, steps, events
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("objective", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("steps_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("replans_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_agent_runs_owner_id", "agent_runs", ["owner_id"])

    op.create_table(
        "agent_run_steps",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("tool", sa.Text(), nullable=True),
        sa.Column("input", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("memento", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("run_id", "seq"),
    )

    op.create_table(
        "run_events",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("run_id", "seq"),
    )

    # 8. Jobs, approvals, tasks, audit_events
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_run_at", "jobs", ["run_at"])

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decision", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approvals_run_id", "approvals", ["run_id"])

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("linked_gap_quantity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("quantities.id"), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tasks_run_id", "tasks", ["run_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("actor", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("prev_hash", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])


def downgrade() -> None:
    # Drop tables in reverse topological dependency order
    op.drop_table("audit_events")
    op.drop_table("tasks")
    op.drop_table("approvals")
    op.drop_table("jobs")
    op.drop_table("run_events")
    op.drop_table("agent_run_steps")
    op.drop_table("agent_runs")
    op.drop_table("simulation_runs")
    op.drop_table("scenarios")
    op.drop_table("business_profiles")
    op.drop_table("policy_rules")
    op.drop_table("policy_documents")
    op.drop_table("quantities")
    op.drop_table("facilities")
    op.drop_table("geo_units")
    op.drop_table("source_versions")
    op.drop_table("sources")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
