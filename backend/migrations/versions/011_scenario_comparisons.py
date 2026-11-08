"""Persist owner-scoped, quantity-linked scenario comparisons."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_scenario_comparisons"
down_revision: Union[str, None] = "010_policy_rule_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scenario_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("left_scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("right_scenario_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("metric_results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("left_scenario_id <> right_scenario_id", name="check_scenario_comparison_distinct_scenarios"),
        sa.CheckConstraint("status IN ('COMPLETED','PARTIAL','INSUFFICIENT_DATA')", name="check_scenario_comparison_status"),
    )
    op.create_index("ix_scenario_comparisons_owner_id", "scenario_comparisons", ["owner_id"])
    op.create_index("ix_scenario_comparisons_left_scenario_id", "scenario_comparisons", ["left_scenario_id"])
    op.create_index("ix_scenario_comparisons_right_scenario_id", "scenario_comparisons", ["right_scenario_id"])


def downgrade() -> None:
    op.drop_index("ix_scenario_comparisons_right_scenario_id", table_name="scenario_comparisons")
    op.drop_index("ix_scenario_comparisons_left_scenario_id", table_name="scenario_comparisons")
    op.drop_index("ix_scenario_comparisons_owner_id", table_name="scenario_comparisons")
    op.drop_table("scenario_comparisons")

