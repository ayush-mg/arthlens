"""Persist proposed agent actions behind explicit user confirmation."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024_agent_action_confirmation"
down_revision: Union[str, None] = "023_decision_version_graphs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_proposed_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="PENDING_CONFIRMATION"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('PENDING_CONFIRMATION','CONFIRMED','REJECTED')",
            name="check_agent_proposed_action_status",
        ),
        sa.CheckConstraint(
            "action_type IN ('CREATE_GOAL','CREATE_TASK','GENERATE_REPORT')",
            name="check_agent_proposed_action_type",
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_proposed_actions_business_id", "agent_proposed_actions", ["business_id"])
    op.create_index("ix_agent_proposed_actions_session_id", "agent_proposed_actions", ["session_id"])
    op.create_index("ix_agent_proposed_actions_session_status", "agent_proposed_actions", ["session_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_agent_proposed_actions_session_status", table_name="agent_proposed_actions")
    op.drop_index("ix_agent_proposed_actions_session_id", table_name="agent_proposed_actions")
    op.drop_index("ix_agent_proposed_actions_business_id", table_name="agent_proposed_actions")
    op.drop_table("agent_proposed_actions")
