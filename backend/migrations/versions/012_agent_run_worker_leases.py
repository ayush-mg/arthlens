"""Add worker leases, recovery attempts, and lease indexes to agent_runs."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_agent_run_worker_leases"
down_revision: Union[str, None] = "011_scenario_comparisons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("claimed_by", sa.Text(), nullable=True))
    op.add_column("agent_runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_runs", sa.Column("recovery_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_runs", sa.Column("max_recovery_attempts", sa.Integer(), nullable=False, server_default="3"))
    op.create_index("ix_agent_runs_lease", "agent_runs", ["state", "lease_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_runs_lease", table_name="agent_runs")
    op.drop_column("agent_runs", "max_recovery_attempts")
    op.drop_column("agent_runs", "recovery_attempts")
    op.drop_column("agent_runs", "lease_expires_at")
    op.drop_column("agent_runs", "claimed_by")

