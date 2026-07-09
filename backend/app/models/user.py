"""
User ORM model.

Represents an authenticated user with role-based access control
and login audit tracking.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """Enumeration of user roles for RBAC."""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    AUDITOR = "auditor"


class UserStatus(str, enum.Enum):
    """Enumeration of user account statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base, TimestampMixin):
    """
    User model with RBAC support and login audit fields.

    Stores authentication credentials, profile information,
    authorization context, and login tracking data.
    """

    __tablename__ = "users"

    __table_args__ = (
        {"comment": "Application users with role-based access control"},
    )

    # ── Primary Key ─────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="UUID v4 primary key",
    )

    # ── Authentication ──────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
        comment="Verified email address (used as login identifier)",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Bcrypt hash of the password",
    )

    # ── Profile ─────────────────────────────────────────────────────────
    display_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Display name shown in the UI",
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="URL to the user's avatar image",
    )

    # ── Authorization ───────────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
        index=True,
        comment="RBAC role determining access level",
    )

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Account status (active, suspended, etc.)",
    )

    # ── Flags ───────────────────────────────────────────────────────────
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the email address has been verified",
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Superuser flag (bypasses all permission checks)",
    )

    # ── Login Audit Fields ──────────────────────────────────────────────
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the last successful login",
    )

    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address of the last successful login (IPv4 or IPv6)",
    )

    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Consecutive failed login attempt count since last successful login",
    )

    # ── Convenience Properties ──────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Check if the user account is active."""
        return self.status == UserStatus.ACTIVE

    @property
    def is_admin(self) -> bool:
        """Check if the user has the admin role."""
        return self.role == UserRole.ADMIN or self.is_superuser

    def record_failed_login(self) -> None:
        """Increment the failed login attempt counter."""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1

    def record_successful_login(self, ip_address: Optional[str]) -> None:
        """Reset failed attempts and record login metadata."""
        self.failed_login_attempts = 0
        self.last_login_ip = ip_address

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role.value}>"
