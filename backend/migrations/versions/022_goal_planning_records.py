"""Add goal milestones, assigned action tasks, and evidence backed snapshots."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022_goal_planning_records"
down_revision: Union[str, None] = "021_business_scenario_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goal_milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("target_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("goal_id", "target_date", name="uq_goal_milestone_date"),
    )
    op.create_index("ix_goal_milestones_business_id", "goal_milestones", ["business_id"])
    op.create_index("ix_goal_milestones_goal_id", "goal_milestones", ["goal_id"])

    op.create_table(
        "goal_action_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('ACTIVE','COMPLETED','CANCELLED')", name="check_goal_action_plan_status"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goal_action_plans_business_id", "goal_action_plans", ["business_id"])
    op.create_index("ix_goal_action_plans_goal_id", "goal_action_plans", ["goal_id"])

    op.create_table(
        "goal_action_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("assigned_member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default="3"),
        sa.Column("status", sa.Text(), nullable=False, server_default="TODO"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("expected_financial_impact", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('TODO','IN_PROGRESS','COMPLETED','BLOCKED')", name="check_goal_action_task_status"),
        sa.CheckConstraint("priority BETWEEN 1 AND 5", name="check_goal_action_task_priority"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["goal_action_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_member_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("business_id", "goal_id", "plan_id", "assigned_member_id"):
        op.create_index(f"ix_goal_action_tasks_{column}", "goal_action_tasks", [column])

    op.create_table(
        "goal_progress_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("planned_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("actual_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("deviation_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("evidence_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('ON_TRACK','AT_RISK','BEHIND','ACHIEVED')", name="check_goal_progress_snapshot_status"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goal_progress_snapshot_business_id", "goal_progress_snapshots", ["business_id"])
    op.create_index("ix_goal_progress_snapshot_goal_id", "goal_progress_snapshots", ["goal_id"])
    op.create_index("ix_goal_progress_snapshot_goal_date", "goal_progress_snapshots", ["goal_id", "as_of_date"])


def downgrade() -> None:
    op.drop_index("ix_goal_progress_snapshot_goal_date", table_name="goal_progress_snapshots")
    op.drop_index("ix_goal_progress_snapshot_goal_id", table_name="goal_progress_snapshots")
    op.drop_index("ix_goal_progress_snapshot_business_id", table_name="goal_progress_snapshots")
    op.drop_table("goal_progress_snapshots")
    for column in ("assigned_member_id", "plan_id", "goal_id", "business_id"):
        op.drop_index(f"ix_goal_action_tasks_{column}", table_name="goal_action_tasks")
    op.drop_table("goal_action_tasks")
    op.drop_index("ix_goal_action_plans_goal_id", table_name="goal_action_plans")
    op.drop_index("ix_goal_action_plans_business_id", table_name="goal_action_plans")
    op.drop_table("goal_action_plans")
    op.drop_index("ix_goal_milestones_goal_id", table_name="goal_milestones")
    op.drop_index("ix_goal_milestones_business_id", table_name="goal_milestones")
    op.drop_table("goal_milestones")
