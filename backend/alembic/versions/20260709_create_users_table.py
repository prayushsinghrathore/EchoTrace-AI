"""
Create users table with RBAC support.

Revision ID: 002_add_users
Revises: 001_initial
Create Date: 2026-07-09
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002_add_users"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the users table."""
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            index=True,
            comment="UUID v4 primary key",
        ),
        sa.Column(
            "email",
            sa.String(320),
            unique=True,
            nullable=False,
            index=True,
            comment="Verified email address (used as login identifier)",
        ),
        sa.Column(
            "hashed_password",
            sa.String(128),
            nullable=False,
            comment="Bcrypt hash of the password",
        ),
        sa.Column(
            "display_name",
            sa.String(150),
            nullable=True,
            comment="Display name shown in the UI",
        ),
        sa.Column(
            "avatar_url",
            sa.String(512),
            nullable=True,
            comment="URL to the user's avatar image",
        ),
        sa.Column(
            "role",
            sa.Enum(
                "admin", "user", "viewer", "auditor",
                name="user_role",
                create_constraint=True,
            ),
            nullable=False,
            server_default="user",
            index=True,
            comment="RBAC role determining access level",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active", "inactive", "suspended", "pending_verification",
                name="user_status",
                create_constraint=True,
            ),
            nullable=False,
            server_default="active",
            index=True,
            comment="Account status (active, suspended, etc.)",
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether the email address has been verified",
        ),
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Superuser flag (bypasses all permission checks)",
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of the last successful login",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp when the record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Timestamp when the record was last updated",
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        comment="Application users with role-based access control",
    )


def downgrade() -> None:
    """Drop the users table and enum types."""
    op.drop_table("users")

    # Drop enum types (PostgreSQL-specific)
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS user_status")
