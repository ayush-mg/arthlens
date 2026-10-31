"""auth_immutability_and_roles

Revision ID: 004_auth_immutability_and_roles
Revises: 003_enforce_exact_integer_seed
Create Date: 2026-10-31 04:00:00.000000

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1, Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Resolves:
1. Seeds the three MVP roles: ENTREPRENEUR, STEWARD, ADMIN into the roles table.
2. Installs database trigger trg_audit_events_immutable to enforce append-only
   immutability on audit_events at the PostgreSQL engine boundary (rejecting UPDATE/DELETE).
3. Creates table revoked_tokens for shared JWT invalidation upon logout.
4. Creates table rate_limits for atomic, concurrency-safe distributed rate limiting.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "004_auth_immutability_and_roles"
down_revision: Union[str, None] = "003_enforce_exact_integer_seed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Seed MVP roles
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Text),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        roles_table,
        [
            {"id": "ENTREPRENEUR", "description": "Entrepreneur creating scenarios and runs"},
            {"id": "STEWARD", "description": "Domain steward approving rules and managing sources"},
            {"id": "ADMIN", "description": "System administrator managing users, quotas, and audit"},
        ],
    )

    # 2. Database trigger on audit_events to reject UPDATE and DELETE
    op.execute("""
    CREATE OR REPLACE FUNCTION enforce_audit_events_immutable()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'audit_events is append-only: updates and deletes are prohibited';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_audit_events_immutable
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW
    EXECUTE FUNCTION enforce_audit_events_immutable();
    """)

    # 3. Table for revoked JWT identifiers (session termination)
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.Text(), primary_key=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"])

    # 4. Table for concurrency-safe atomic distributed rate limiting
    op.create_table(
        "rate_limits",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_rate_limits_reset_at", "rate_limits", ["reset_at"])


def downgrade() -> None:
    # 1. Drop rate_limits table
    op.drop_index("ix_rate_limits_reset_at", table_name="rate_limits")
    op.drop_table("rate_limits")

    # 2. Drop revoked_tokens table
    op.drop_index("ix_revoked_tokens_expires_at", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")

    # 3. Drop trigger and function on audit_events
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_immutable ON audit_events;")
    op.execute("DROP FUNCTION IF EXISTS enforce_audit_events_immutable();")

    # 4. Remove seeded roles
    op.execute("DELETE FROM roles WHERE id IN ('ENTREPRENEUR', 'STEWARD', 'ADMIN');")
