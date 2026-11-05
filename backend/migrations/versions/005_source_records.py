"""source_records

Revision ID: 005_source_records
Revises: 004_auth_immutability_and_roles
Create Date: 2026-11-05 17:35:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.5 Step 9, Part 9.1).
Phase: Phase 2 (P2-1 Step 9 Persistence Completion).

Creates table source_records to durably persist normalized records, preserving:
- source_id and source_version_id references
- original raw fields (JSONB)
- normalized domain fields (JSONB)
- canonical unit definitions (JSONB)
- geographic reconciliation outcomes (resolved flag, canonical LGD ID, unresolved raw ID, resolution tier)
- temporal support and as_of dates
- provenance and licence metadata
- unique constraint (source_version_id, record_id) for snapshot idempotency
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "005_source_records"
down_revision: Union[str, None] = "004_auth_immutability_and_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "source_records",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source_id", sa.Text(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_version_id", sa.Text(), sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_id", sa.Text(), nullable=False),
        sa.Column("original_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("canonical_units", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("geo_resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("geo_unit_id", sa.Text(), nullable=True),
        sa.Column("unresolved_raw_id", sa.Text(), nullable=True),
        sa.Column("resolution_tier", sa.SmallInteger(), nullable=True),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("temporal_support", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("license_name", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source_version_id", "record_id", name="uq_source_records_version_record"),
    )
    op.create_index("ix_source_records_source_id", "source_records", ["source_id"])
    op.create_index("ix_source_records_source_version_id", "source_records", ["source_version_id"])
    op.create_index("ix_source_records_record_id", "source_records", ["record_id"])
    op.create_index("ix_source_records_geo_unit_id", "source_records", ["geo_unit_id"])


def downgrade() -> None:
    op.drop_index("ix_source_records_geo_unit_id", table_name="source_records")
    op.drop_index("ix_source_records_record_id", table_name="source_records")
    op.drop_index("ix_source_records_source_version_id", table_name="source_records")
    op.drop_index("ix_source_records_source_id", table_name="source_records")
    op.drop_table("source_records")

