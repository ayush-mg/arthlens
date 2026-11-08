"""geo_unit_geometry_source_record

Revision ID: 008_geo_unit_geometry_source_record
Revises: 007_geo_check_constraints
Create Date: 2026-11-07 09:30:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 9.1).
Phase: Phase 2 (P2-2 Administrative Boundaries & Exact Provenance Linkage).

Links boundary geometries in geo_units directly and foreign-keyed to the exact
source_records.id from which they were ingested.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic. Length <= 32 chars.
revision: str = "008_geo_unit_geom_source"
down_revision: Union[str, None] = "007_geo_check_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable geometry_source_record_id column
    op.add_column(
        "geo_units",
        sa.Column("geometry_source_record_id", sa.Text(), nullable=True),
    )

    # 2. Add foreign key referencing source_records.id
    op.create_foreign_key(
        "fk_geo_units_geometry_source_record_id",
        "geo_units",
        "source_records",
        ["geometry_source_record_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Create index for fast lookups
    op.create_index(
        "ix_geo_units_geometry_source_record_id",
        "geo_units",
        ["geometry_source_record_id"],
    )

    # 4. Backfill existing records with boundary geometry ONLY where there is a unique, unambiguous DS-09 source_record
    op.execute(
        sa.text("""
        UPDATE geo_units u
        SET geometry_source_record_id = sub.id
        FROM (
            SELECT geo_unit_id, MIN(id) as id
            FROM source_records
            WHERE source_id = 'DS-09'
            GROUP BY geo_unit_id
            HAVING COUNT(*) = 1
        ) sub
        WHERE u.geometry IS NOT NULL
          AND u.id = sub.geo_unit_id
          AND u.geometry_source_record_id IS NULL;
        """)
    )


def downgrade() -> None:
    op.drop_index("ix_geo_units_geometry_source_record_id", table_name="geo_units")
    op.drop_constraint("fk_geo_units_geometry_source_record_id", "geo_units", type_="foreignkey")
    op.drop_column("geo_units", "geometry_source_record_id")

