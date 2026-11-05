"""geo_check_constraints

Revision ID: 007_geo_check_constraints
Revises: 006_geo_coverage_status
Create Date: 2026-11-06 00:30:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 9.1).
Phase: Phase 2 (P2-2 Stage 2 Status Integrity and Check Constraints).

Enforces check constraints for orthogonal geographic coverage dimensions:
1. coverage_status IN ('NAVIGABLE', 'HIERARCHY_UNRESOLVED')
2. geometry_status IN ('GEOMETRY_VERIFIED', 'GEOMETRY_SIMPLIFIED', 'GEOMETRY_HISTORICAL', 'GEOMETRY_UNVALIDATED', 'GEOMETRY_MISSING')
3. analytical_status IN ('ANALYSABLE', 'ANALYSIS_UNAVAILABLE')
4. Backfills existing records where geometry IS NOT NULL and geometry_status is GEOMETRY_MISSING to GEOMETRY_UNVALIDATED.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic. Length <= 32 chars.
revision: str = "007_geo_check_constraints"
down_revision: Union[str, None] = "006_geo_coverage_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Backfill existing records with geometry present to GEOMETRY_UNVALIDATED
    op.execute(
        sa.text("""
        UPDATE geo_units
        SET geometry_status = 'GEOMETRY_UNVALIDATED'
        WHERE geometry IS NOT NULL AND geometry_status = 'GEOMETRY_MISSING';
        """)
    )

    # 2. Add CHECK constraints
    op.create_check_constraint(
        "check_geo_unit_coverage_status",
        "geo_units",
        "coverage_status IN ('NAVIGABLE', 'HIERARCHY_UNRESOLVED')",
    )
    op.create_check_constraint(
        "check_geo_unit_geometry_status",
        "geo_units",
        "geometry_status IN ('GEOMETRY_VERIFIED', 'GEOMETRY_SIMPLIFIED', 'GEOMETRY_HISTORICAL', 'GEOMETRY_UNVALIDATED', 'GEOMETRY_MISSING')",
    )
    op.create_check_constraint(
        "check_geo_unit_analytical_status",
        "geo_units",
        "analytical_status IN ('ANALYSABLE', 'ANALYSIS_UNAVAILABLE')",
    )


def downgrade() -> None:
    op.drop_constraint("check_geo_unit_analytical_status", "geo_units", type_="check")
    op.drop_constraint("check_geo_unit_geometry_status", "geo_units", type_="check")
    op.drop_constraint("check_geo_unit_coverage_status", "geo_units", type_="check")

