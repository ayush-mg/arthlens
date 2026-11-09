"""Add priority column and check constraints to tasks table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_task_priority"
down_revision: Union[str, None] = "012_agent_run_worker_leases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("priority", sa.Text(), nullable=False, server_default="MEDIUM"),
    )
    op.create_check_constraint(
        "check_task_status",
        "tasks",
        "status IN ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')",
    )
    op.create_check_constraint(
        "check_task_priority",
        "tasks",
        "priority IN ('HIGH', 'MEDIUM', 'LOW')",
    )


def downgrade() -> None:
    op.drop_constraint("check_task_priority", "tasks", type_="check")
    op.drop_constraint("check_task_status", "tasks", type_="check")
    op.drop_column("tasks", "priority")
