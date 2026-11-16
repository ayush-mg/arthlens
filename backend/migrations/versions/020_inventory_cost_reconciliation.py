"""Add durable inventory cost reconciliation state and event history."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020_inventory_cost_reconciliation"
down_revision: Union[str, None] = "019_purchase_returns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The standard Alembic version table uses VARCHAR(32), but this and later
    # descriptive revision identifiers exceed that limit. Widen it before
    # Alembic records this revision so upgrade head succeeds on fresh databases.
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )
    op.add_column(
        "purchases",
        sa.Column("return_credit_amount", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
    )
    op.create_check_constraint(
        "check_purchase_return_credit_nonnegative",
        "purchases",
        "return_credit_amount >= 0",
    )
    op.add_column(
        "inventory_movements",
        sa.Column("cost_reconciliation_status", sa.String(length=32), nullable=False, server_default="VERIFIED"),
    )
    op.add_column(
        "inventory_movements",
        sa.Column("source_purchase_item_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_inventory_movements_source_purchase_item",
        "inventory_movements",
        "purchase_items",
        ["source_purchase_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("inventory_movements", sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "inventory_movements",
        sa.Column("reconciled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("inventory_movements", sa.Column("reconciliation_note", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_inventory_movements_reconciled_by_user",
        "inventory_movements",
        "users",
        ["reconciled_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "check_inventory_cost_reconciliation_status",
        "inventory_movements",
        "cost_reconciliation_status IN ('VERIFIED', 'UNRECONCILED', 'ESTIMATED', 'CONFLICTING')",
    )

    # A purchase movement has a durable purchase reference and a matching line
    # with the same product, quantity, and unit price. That relationship is
    # sufficient to recover the original cost without estimating.
    op.execute(sa.text("""
        UPDATE inventory_movements AS movement
        SET cost_basis = movement.unit_price,
            source_purchase_item_id = CASE WHEN (
                SELECT COUNT(*)
                FROM purchase_items AS item
                WHERE item.purchase_id::text = movement.reference_id
                  AND item.product_id = movement.product_id
                  AND item.quantity = movement.quantity
                  AND item.unit_price = movement.unit_price
            ) = 1 THEN (
                SELECT item.id
                FROM purchase_items AS item
                WHERE item.purchase_id::text = movement.reference_id
                  AND item.product_id = movement.product_id
                  AND item.quantity = movement.quantity
                  AND item.unit_price = movement.unit_price
            ) ELSE NULL END,
            cost_reconciliation_status = 'VERIFIED'
        WHERE movement.movement_type = 'PURCHASE'
          AND EXISTS (
              SELECT 1
              FROM purchases AS purchase
              JOIN purchase_items AS item ON item.purchase_id = purchase.id
              WHERE purchase.id::text = movement.reference_id
                AND purchase.business_id = movement.business_id
                AND item.product_id = movement.product_id
                AND item.quantity = movement.quantity
                AND item.unit_price = movement.unit_price
          )
    """))

    # Link historical purchase-return movements to their immutable source line
    # only when the match is unique. Ambiguous duplicates remain unlinked for
    # explicit review during the reconciliation run.
    op.execute(sa.text("""
        UPDATE inventory_movements AS movement
        SET source_purchase_item_id = item.purchase_item_id
        FROM purchase_return_items AS item
        JOIN purchase_returns AS return_record ON return_record.id = item.purchase_return_id
        WHERE movement.reference_id = return_record.id::text
          AND movement.movement_type = 'RETURN'
          AND movement.product_id = item.product_id
          AND movement.quantity = item.quantity
          AND movement.unit_price = item.original_unit_price
          AND (
              SELECT COUNT(*)
              FROM purchase_return_items AS candidate
              WHERE candidate.purchase_return_id = item.purchase_return_id
                AND candidate.product_id = movement.product_id
                AND candidate.quantity = movement.quantity
                AND candidate.original_unit_price = movement.unit_price
          ) = 1
    """))

    # Do not infer that a zero basis is valid from the mere presence of some
    # zero-price purchase for the same product. Chronological replay can prove
    # a fully supported zero-cost stream; ambiguous historical zeroes remain open.
    op.execute(sa.text("""
        UPDATE inventory_movements
        SET cost_reconciliation_status = 'UNRECONCILED'
        WHERE cost_basis IS NULL
           OR (
                cost_basis = 0
                AND movement_type IN ('SALE', 'RETURN', 'OPENING', 'ADJUSTMENT')
           )
    """))

    op.create_table(
        "inventory_cost_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_cost_reconciliations_business_created",
        "inventory_cost_reconciliations",
        ["business_id", "created_at"],
    )

    op.create_table(
        "inventory_cost_reconciliation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reconciliation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("classification", sa.String(length=40), nullable=False),
        sa.Column("prior_cost_basis", sa.Numeric(14, 2), nullable=True),
        sa.Column("resolved_cost_basis", sa.Numeric(14, 2), nullable=True),
        sa.Column("source_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("resolution_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["reconciliation_id"], ["inventory_cost_reconciliations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["movement_id"], ["inventory_movements.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_cost_reconciliation_events_run_product",
        "inventory_cost_reconciliation_events",
        ["reconciliation_id", "product_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_cost_reconciliation_events_run_product", table_name="inventory_cost_reconciliation_events")
    op.drop_table("inventory_cost_reconciliation_events")
    op.drop_index("ix_inventory_cost_reconciliations_business_created", table_name="inventory_cost_reconciliations")
    op.drop_table("inventory_cost_reconciliations")
    op.drop_constraint("check_inventory_cost_reconciliation_status", "inventory_movements", type_="check")
    op.drop_constraint("fk_inventory_movements_reconciled_by_user", "inventory_movements", type_="foreignkey")
    op.drop_constraint("fk_inventory_movements_source_purchase_item", "inventory_movements", type_="foreignkey")
    op.drop_column("inventory_movements", "reconciliation_note")
    op.drop_column("inventory_movements", "source_purchase_item_id")
    op.drop_column("inventory_movements", "reconciled_by_user_id")
    op.drop_column("inventory_movements", "reconciled_at")
    op.drop_column("inventory_movements", "cost_reconciliation_status")
    op.drop_constraint("check_purchase_return_credit_nonnegative", "purchases", type_="check")
    op.drop_column("purchases", "return_credit_amount")
