"""geo_coverage_status

Revision ID: 006_geo_coverage_status
Revises: 005_source_records
Create Date: 2026-11-05 23:15:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 9.1).
Phase: Phase 2 (P2-2.2 Geographic Coverage Semantics & Adapter Hardening).

Decouples geographic coverage semantics into three orthogonal dimensions:
1. Navigation status / coverage_status (server default updated from 'FULL' to 'NAVIGABLE')
2. Geometry availability status: geometry_status (GEOMETRY_VERIFIED, GEOMETRY_SIMPLIFIED, GEOMETRY_HISTORICAL, GEOMETRY_MISSING)
3. Analytical evidence status: analytical_status (ANALYSABLE, ANALYSIS_UNAVAILABLE)
4. Adds historical census_code to geo_units for Census MDDS cross-referencing.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_geo_coverage_status"
down_revision: Union[str, None] = "005_source_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update default for coverage_status from FULL to NAVIGABLE
    op.alter_column("geo_units", "coverage_status", server_default="NAVIGABLE")

    # Add geometry_status column
    op.add_column(
        "geo_units",
        sa.Column("geometry_status", sa.Text(), nullable=False, server_default="GEOMETRY_MISSING"),
    )

    # Add analytical_status column
    op.add_column(
        "geo_units",
        sa.Column("analytical_status", sa.Text(), nullable=False, server_default="ANALYSIS_UNAVAILABLE"),
    )

    # Add census_code column
    op.add_column(
        "geo_units",
        sa.Column("census_code", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("geo_units", "census_code")
    op.drop_column("geo_units", "analytical_status")
    op.drop_column("geo_units", "geometry_status")
    op.alter_column("geo_units", "coverage_status", server_default="FULL")

