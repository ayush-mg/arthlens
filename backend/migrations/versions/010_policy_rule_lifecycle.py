"""Add source-verified policy lifecycle, immutable versions, and evaluation audit."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_policy_rule_lifecycle"
down_revision: Union[str, None] = "009_road_graph_spatial_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("policy_documents", sa.Column("source_version_id", sa.Text(), nullable=True))
    op.add_column("policy_documents", sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("policy_documents", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policy_documents", sa.Column("review_note", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_policy_documents_source_version_id",
        "policy_documents",
        "source_versions",
        ["source_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_policy_documents_verified_by",
        "policy_documents",
        "users",
        ["verified_by"],
        ["id"],
    )
    op.create_index("ix_policy_documents_source_version_id", "policy_documents", ["source_version_id"])
    op.alter_column(
        "policy_documents",
        "status",
        existing_type=sa.Text(),
        server_default=sa.text("'PENDING_REVIEW'"),
    )
    op.execute(
        "UPDATE policy_documents SET status = 'PENDING_REVIEW', verified_by = NULL, verified_at = NULL, "
        "review_note = 'Legacy document status downgraded: steward review and exact source-version provenance were not recorded.' "
        "WHERE status = 'ACTIVE'"
    )
    op.create_check_constraint(
        "check_policy_document_status",
        "policy_documents",
        "status IN ('PENDING_REVIEW','VERIFIED','REJECTED')",
    )

    op.add_column("policy_rules", sa.Column("rule_key", sa.Text(), nullable=True))
    op.add_column(
        "policy_rules",
        sa.Column(
            "evidence_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "policy_rules",
        sa.Column(
            "source_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("policy_rules", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policy_rules", sa.Column("approval_note", sa.Text(), nullable=True))
    op.add_column("policy_rules", sa.Column("retired_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("policy_rules", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policy_rules", sa.Column("retirement_reason", sa.Text(), nullable=True))
    op.execute("UPDATE policy_rules SET rule_key = 'legacy-' || id::text WHERE rule_key IS NULL")
    op.execute(
        "UPDATE policy_rules SET status = 'DRAFT', approved_by = NULL, approved_at = NULL, "
        "approval_note = 'Legacy status downgraded: source verification and approval provenance were not recorded.' "
        "WHERE status = 'APPROVED'"
    )
    op.alter_column("policy_rules", "rule_key", existing_type=sa.Text(), nullable=False)
    op.create_foreign_key(
        "fk_policy_rules_retired_by",
        "policy_rules",
        "users",
        ["retired_by"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_policy_scheme_rule_version",
        "policy_rules",
        ["scheme_id", "rule_key", "version"],
    )
    op.create_check_constraint(
        "check_policy_effective_period",
        "policy_rules",
        "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
    )

    op.create_table(
        "policy_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_id", sa.Text(), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("policy_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rule_key", sa.Text(), nullable=False),
        sa.Column("rule_version", sa.Text(), nullable=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("fact_quantity_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("trace", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("outcome IN ('TRUE','FALSE','UNKNOWN')", name="check_policy_evaluation_outcome"),
        sa.CheckConstraint(
            "status IN ('RULE_UNAVAILABLE','INSUFFICIENT_DATA','SCENARIO_ONLY','ASSESSED')",
            name="check_policy_evaluation_status",
        ),
    )
    op.create_index("ix_policy_evaluations_owner_id", "policy_evaluations", ["owner_id"])
    op.create_index("ix_policy_evaluations_scheme_id", "policy_evaluations", ["scheme_id"])


def downgrade() -> None:
    op.drop_index("ix_policy_evaluations_scheme_id", table_name="policy_evaluations")
    op.drop_index("ix_policy_evaluations_owner_id", table_name="policy_evaluations")
    op.drop_table("policy_evaluations")
    op.drop_constraint("check_policy_effective_period", "policy_rules", type_="check")
    op.drop_constraint("uq_policy_scheme_rule_version", "policy_rules", type_="unique")
    op.drop_constraint("fk_policy_rules_retired_by", "policy_rules", type_="foreignkey")
    for column in (
        "retirement_reason",
        "retired_at",
        "retired_by",
        "approval_note",
        "approved_at",
        "source_references",
        "evidence_requirements",
        "rule_key",
    ):
        op.drop_column("policy_rules", column)
    op.drop_index("ix_policy_documents_source_version_id", table_name="policy_documents")
    op.drop_constraint("fk_policy_documents_verified_by", "policy_documents", type_="foreignkey")
    op.drop_constraint("fk_policy_documents_source_version_id", "policy_documents", type_="foreignkey")
    for column in ("review_note", "verified_at", "verified_by", "source_version_id"):
        op.drop_column("policy_documents", column)
    op.alter_column(
        "policy_documents",
        "status",
        existing_type=sa.Text(),
        server_default=sa.text("'ACTIVE'"),
    )
    op.drop_constraint("check_policy_document_status", "policy_documents", type_="check")
