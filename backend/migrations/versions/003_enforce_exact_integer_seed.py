"""enforce_exact_integer_seed

Revision ID: 003_enforce_exact_integer_seed
Revises: 002_seed_and_immutability
Create Date: 2026-10-30 00:00:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 4.1, 4.5, 6.4, Part 9.1, 9.2).
Phase: P1-5 (Exact Seed Precision and Validation Audit).

Resolves:
1. Migrates simulation_runs.seed to unconstrained NUMERIC with check constraint
   `seed = TRUNC(seed) AND seed >= 0 AND seed <= 18446744073709551615`
   to ensure that PostgreSQL strictly rejects fractional seeds (rather than silently
   rounding them at the column scale definition boundary), while preserving the full
   unsigned 64-bit integer range without loss of precision.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_enforce_exact_integer_seed"
down_revision: Union[str, None] = "002_seed_and_immutability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the previous check constraint from 002
    op.drop_constraint("check_simulation_run_seed_range", "simulation_runs", type_="check")

    # 2. Alter column to unconstrained NUMERIC
    op.alter_column(
        "simulation_runs",
        "seed",
        type_=sa.Numeric(),
        existing_type=sa.Numeric(precision=20, scale=0),
        nullable=False,
    )

    # 3. Add strengthened constraint rejecting fractional seeds and enforcing uint64 range
    op.create_check_constraint(
        "check_simulation_run_seed_range",
        "simulation_runs",
        "seed = TRUNC(seed) AND seed >= 0 AND seed <= 18446744073709551615",
    )


def downgrade() -> None:
    # 0. Safety check: refuse downgrade if any fractional seed exists
    bind = op.get_bind()
    count = bind.execute(
        sa.text("SELECT count(*) FROM simulation_runs WHERE seed != TRUNC(seed)")
    ).scalar()
    if count and count > 0:
        raise ValueError(
            f"Cannot downgrade migration 003_enforce_exact_integer_seed: "
            f"found {count} simulation_run record(s) with fractional seed values. "
            "Downgrading to NUMERIC(20, 0) would silently round fractional values."
        )

    # 1. Revert constraint
    op.drop_constraint("check_simulation_run_seed_range", "simulation_runs", type_="check")

    # 2. Revert to NUMERIC(20, 0)
    op.alter_column(
        "simulation_runs",
        "seed",
        type_=sa.Numeric(precision=20, scale=0),
        existing_type=sa.Numeric(),
        nullable=False,
    )

    # 3. Restore 002 range constraint
    op.create_check_constraint(
        "check_simulation_run_seed_range",
        "simulation_runs",
        "seed >= 0 AND seed <= 18446744073709551615",
    )
