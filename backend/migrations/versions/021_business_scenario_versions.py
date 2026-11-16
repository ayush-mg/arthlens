"""Add tenant scoped immutable scenarios and reproducible simulation runs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021_business_scenario_versions"
down_revision: Union[str, None] = "020_inventory_cost_reconciliation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "name", name="uq_business_scenarios_name"),
    )
    op.create_index("ix_business_scenarios_business_id", "business_scenarios", ["business_id"])

    op.create_table(
        "business_scenario_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("baseline_snapshot_hash", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["scenario_id"], ["business_scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id", "version_number", name="uq_business_scenario_version"),
    )
    op.create_index("ix_business_scenario_versions_scenario_id", "business_scenario_versions", ["scenario_id"])

    op.create_table(
        "business_simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("random_seed", sa.Numeric(20, 0), nullable=False),
        sa.Column("iterations", sa.Integer(), nullable=False),
        sa.Column("distribution_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("baseline_snapshot_hash", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "random_seed = TRUNC(random_seed) AND random_seed >= 0 AND random_seed <= 18446744073709551615",
            name="check_business_simulation_seed_range",
        ),
        sa.CheckConstraint("iterations >= 1 AND iterations <= 100000", name="check_business_simulation_iterations"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_version_id"], ["business_scenario_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_business_simulation_runs_business_id", "business_simulation_runs", ["business_id"])
    op.create_index("ix_business_simulation_runs_scenario_version_id", "business_simulation_runs", ["scenario_version_id"])


def downgrade() -> None:
    op.drop_index("ix_business_simulation_runs_scenario_version_id", table_name="business_simulation_runs")
    op.drop_index("ix_business_simulation_runs_business_id", table_name="business_simulation_runs")
    op.drop_table("business_simulation_runs")
    op.drop_index("ix_business_scenario_versions_scenario_id", table_name="business_scenario_versions")
    op.drop_table("business_scenario_versions")
    op.drop_index("ix_business_scenarios_business_id", table_name="business_scenarios")
    op.drop_table("business_scenarios")
