"""Add agent sessions, turns, and payment idempotency key (Mandates 3 & 5)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015_agent_sessions"
down_revision: Union[str, None] = "014_business_operating_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. agent_sessions
    op.create_table(
        "agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 2. agent_session_turns
    op.create_table(
        "agent_session_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("extracted_parameters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("data_gaps", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("follow_up_questions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("plan_steps", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("decision_outcome", sa.Text(), nullable=True),
        sa.Column("synthesis", sa.Text(), nullable=False),
        sa.Column("planning_attribution", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("synthesis_attribution", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 3. Add idempotency_key to payments
    op.add_column("payments", sa.Column("idempotency_key", sa.Text(), nullable=True))
    op.create_index("ix_payments_idempotency_key", "payments", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_payments_idempotency_key", table_name="payments")
    op.drop_column("payments", "idempotency_key")
    op.drop_table("agent_session_turns")
    op.drop_table("agent_sessions")
