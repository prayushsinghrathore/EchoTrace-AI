"""
Add login audit fields, refresh tokens, and password reset tokens.

- Adds last_login_ip and failed_login_attempts to users
- Creates refresh_tokens table (rotation/revocation)
- Creates password_reset_tokens table

Revision ID: 003_add_auth_audit
Revises: 002_add_users
Create Date: 2026-07-10
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003_add_auth_audit"
down_revision: Union[str, None] = "002_add_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the migration."""
    # ── Users table: audit columns ──────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "last_login_ip",
            sa.String(45),
            nullable=True,
            comment="IP address of the last successful login (IPv4 or IPv6)",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Consecutive failed login attempt count since last successful login",
        ),
    )

    # ── Refresh tokens table ────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique token record identifier",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="The user this token belongs to",
        ),
        sa.Column(
            "token_jti",
            sa.String(64),
            unique=True,
            nullable=False,
            index=True,
            comment="Unique JWT ID (jti claim) for this refresh token",
        ),
        sa.Column(
            "token_hash",
            sa.String(128),
            nullable=False,
            comment="HMAC-SHA256 hash of the full refresh token string",
        ),
        sa.Column(
            "rotated_from_jti",
            sa.String(64),
            nullable=True,
            comment="JWT ID of the token this one rotated from (null for initial tokens)",
        ),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this token has been revoked",
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When this token was revoked",
        ),
        sa.Column(
            "revoked_by_action",
            sa.String(32),
            nullable=True,
            comment="Action that caused revocation: rotation, logout, admin_revoke",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="IP address that issued this token",
        ),
        sa.Column(
            "user_agent",
            sa.String(512),
            nullable=True,
            comment="User agent that issued this token",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this token naturally expires",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        comment="Stored refresh tokens for rotation and revocation",
    )

    # ── Password reset tokens table ─────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique reset request identifier",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="User requesting the password reset",
        ),
        sa.Column(
            "token_hash",
            sa.String(128),
            nullable=False,
            comment="SHA-256 hash of the password reset JWT for lookup",
        ),
        sa.Column(
            "is_used",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this reset token has been used",
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the password was actually reset",
        ),
        sa.Column(
            "used_by_ip",
            sa.String(45),
            nullable=True,
            comment="IP address that performed the reset",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this reset token expires",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        comment="Password reset request audit records",
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "last_login_ip")
