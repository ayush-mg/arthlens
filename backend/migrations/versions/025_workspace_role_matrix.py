"""Add workspace administrator and analyst roles."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025_workspace_role_matrix"
down_revision: Union[str, None] = "024_agent_action_confirmation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("check_membership_role", "business_memberships", type_="check")
    op.create_check_constraint(
        "check_membership_role",
        "business_memberships",
        "role IN ('OWNER', 'ADMIN', 'MANAGER', 'ACCOUNTANT', 'ANALYST', 'VIEWER')",
    )


def downgrade() -> None:
    op.execute("UPDATE business_memberships SET role='MANAGER' WHERE role='ADMIN'")
    op.execute("UPDATE business_memberships SET role='VIEWER' WHERE role='ANALYST'")
    op.drop_constraint("check_membership_role", "business_memberships", type_="check")
    op.create_check_constraint(
        "check_membership_role",
        "business_memberships",
        "role IN ('OWNER', 'MANAGER', 'ACCOUNTANT', 'VIEWER')",
    )
