"""Store sale-time inventory cost on each movement."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_inv_cost_basis"
down_revision: Union[str, None] = "017_membership_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inventory_movements", sa.Column("cost_basis", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("inventory_movements", "cost_basis")
