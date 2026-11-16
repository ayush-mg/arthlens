"""Add active state to business memberships for revocation and reactivation."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_membership_lifecycle"
down_revision: Union[str, None] = "016_ledger_and_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "business_memberships",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("business_memberships", "is_active")
