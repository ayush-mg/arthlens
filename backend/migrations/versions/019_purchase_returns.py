"""Persist supplier returns against their original purchase lines."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019_purchase_returns"
down_revision: Union[str, None] = "018_inv_cost_basis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchase_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("refund_method", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("subtotal >= 0", name="check_purchase_returns_nonnegative_subtotal"),
        sa.CheckConstraint("tax_amount >= 0", name="check_purchase_returns_nonnegative_tax"),
        sa.CheckConstraint("total_amount = subtotal + tax_amount", name="check_purchase_returns_total"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "idempotency_key", name="uq_purchase_returns_business_idempotency"),
    )
    op.create_index("ix_purchase_returns_business_purchase", "purchase_returns", ["business_id", "purchase_id"])

    op.create_table(
        "purchase_return_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_return_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("original_unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("pretax_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("inventory_cost_removed", sa.Numeric(14, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="check_purchase_return_item_positive_quantity"),
        sa.CheckConstraint("original_unit_price >= 0", name="check_purchase_return_item_nonnegative_price"),
        sa.CheckConstraint("pretax_amount >= 0", name="check_purchase_return_item_nonnegative_pretax"),
        sa.CheckConstraint("tax_amount >= 0", name="check_purchase_return_item_nonnegative_tax"),
        sa.CheckConstraint("inventory_cost_removed >= 0", name="check_purchase_return_item_nonnegative_cost"),
        sa.ForeignKeyConstraint(["purchase_return_id"], ["purchase_returns.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["purchase_item_id"], ["purchase_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_return_id", "purchase_item_id", name="uq_purchase_return_item_line"),
    )
    op.create_index("ix_purchase_return_items_purchase_item", "purchase_return_items", ["purchase_item_id"])


def downgrade() -> None:
    op.drop_index("ix_purchase_return_items_purchase_item", table_name="purchase_return_items")
    op.drop_table("purchase_return_items")
    op.drop_index("ix_purchase_returns_business_purchase", table_name="purchase_returns")
    op.drop_table("purchase_returns")
