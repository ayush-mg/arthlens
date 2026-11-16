"""Persist decision lineage, causal graphs, and evidence records."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023_decision_version_graphs"
down_revision: Union[str, None] = "022_goal_planning_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("decision_evaluations", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("decision_evaluations", sa.Column("parent_decision_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("decision_evaluations", sa.Column("causal_graph", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"))
    op.add_column("decision_evaluations", sa.Column("evidence_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"))
    op.create_foreign_key(
        "fk_decision_evaluations_parent_decision_id",
        "decision_evaluations", "decision_evaluations", ["parent_decision_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_decision_evaluations_parent_decision_id", "decision_evaluations", ["parent_decision_id"])
    op.create_check_constraint("check_decision_version_number_positive", "decision_evaluations", "version_number >= 1")


def downgrade() -> None:
    op.drop_constraint("check_decision_version_number_positive", "decision_evaluations", type_="check")
    op.drop_index("ix_decision_evaluations_parent_decision_id", table_name="decision_evaluations")
    op.drop_constraint("fk_decision_evaluations_parent_decision_id", "decision_evaluations", type_="foreignkey")
    op.drop_column("decision_evaluations", "evidence_items")
    op.drop_column("decision_evaluations", "causal_graph")
    op.drop_column("decision_evaluations", "parent_decision_id")
    op.drop_column("decision_evaluations", "version_number")
