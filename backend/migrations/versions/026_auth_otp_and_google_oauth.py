"""Persist email verification, OTP challenges, and Google account identity."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_auth_otp_and_google_oauth"
down_revision: Union[str, None] = "025_workspace_role_matrix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Existing accounts predate OTP and remain usable; all newly registered accounts
    # must complete the verification challenge before they receive a session.
    op.execute("UPDATE users SET email_verified = TRUE")
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("auth_provider", sa.String(length=32), nullable=False, server_default="local"))
    op.add_column("users", sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)

    op.create_table(
        "auth_otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("purpose IN ('REGISTER_VERIFY','LOGIN_2FA')", name="check_auth_otp_purpose"),
        sa.CheckConstraint("attempts >= 0 AND max_attempts BETWEEN 1 AND 10", name="check_auth_otp_attempts"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_otp_challenges_email", "auth_otp_challenges", ["email"])
    op.create_index(
        "ix_auth_otp_challenges_active_email_purpose",
        "auth_otp_challenges",
        ["email", "purpose", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_otp_challenges_active_email_purpose", table_name="auth_otp_challenges")
    op.drop_index("ix_auth_otp_challenges_email", table_name="auth_otp_challenges")
    op.drop_table("auth_otp_challenges")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "two_factor_enabled")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "email_verified")
