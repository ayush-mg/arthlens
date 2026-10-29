"""fix_simulation_seed_and_quantity_immutability

Revision ID: 002_seed_and_immutability
Revises: 001_initial_schema
Create Date: 2026-10-29 18:00:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 4.1, 4.5, Part 9.1, 9.2).
Phase: P1-5 (Database Integrity & Immutability Hardening).

Resolves:
1. Expands simulation_runs.seed to NUMERIC(20, 0) with 0 <= seed <= 18446744073709551615
   to support the full unsigned 64-bit seed range (PCG64) without overflow.
2. Implements database-level trigger on quantities to enforce immutability of value
   and kind at the PostgreSQL engine boundary, while permitting quality flag supersession.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_seed_and_immutability"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Expand simulation_runs.seed from BIGINT to NUMERIC(20, 0) and add range constraint
    op.alter_column(
        "simulation_runs",
        "seed",
        type_=sa.Numeric(precision=20, scale=0),
        existing_type=sa.BigInteger(),
        nullable=False,
    )
    op.create_check_constraint(
        "check_simulation_run_seed_range",
        "simulation_runs",
        "seed >= 0 AND seed <= 18446744073709551615",
    )

    # 2. Database-level trigger on quantities to reject value and kind updates
    op.execute("""
    CREATE OR REPLACE FUNCTION enforce_quantity_immutability()
    RETURNS TRIGGER AS $$
    BEGIN
        IF (NEW.value IS DISTINCT FROM OLD.value) THEN
            RAISE EXCEPTION 'Quantity % is immutable: value cannot be modified (% -> %)',
                OLD.id, OLD.value, NEW.value;
        END IF;
        IF (NEW.kind IS DISTINCT FROM OLD.kind) THEN
            RAISE EXCEPTION 'Quantity % is immutable: kind cannot be modified (% -> %)',
                OLD.id, OLD.kind, NEW.kind;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_quantities_immutable
    BEFORE UPDATE ON quantities
    FOR EACH ROW
    EXECUTE FUNCTION enforce_quantity_immutability();
    """)


def downgrade() -> None:
    # 0. Safety check: refuse downgrade if out-of-range seeds exist
    bind = op.get_bind()
    count = bind.execute(
        sa.text("SELECT count(*) FROM simulation_runs WHERE seed > 9223372036854775807")
    ).scalar()
    if count and count > 0:
        raise ValueError(
            f"Cannot downgrade migration 002_seed_and_immutability: "
            f"found {count} simulation_run record(s) with seed > 9223372036854775807 (max signed BIGINT). "
            "Downgrading would cause data truncation or loss. Clean or archive out-of-range seeds before downgrading."
        )

    # 1. Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trg_quantities_immutable ON quantities;")
    op.execute("DROP FUNCTION IF EXISTS enforce_quantity_immutability();")

    # 2. Revert simulation_runs.seed
    op.drop_constraint("check_simulation_run_seed_range", "simulation_runs", type_="check")
    op.alter_column(
        "simulation_runs",
        "seed",
        type_=sa.BigInteger(),
        existing_type=sa.Numeric(precision=20, scale=0),
        nullable=False,
    )
