"""
Password reset token model.

Tracks password reset requests for audit and rate-limiting.
Tokens themselves are JWT-based but the request record is persisted.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PasswordResetToken(Base, TimestampMixin):
    """
    Password reset request record.

    Each row represents one password reset request.
    The actual reset is authorized via a JWT token (stored separately),
    but this table tracks the request metadata for audit and rate limiting.
    """

    __tablename__ = "password_reset_tokens"

    __table_args__ = (
        {"comment": "Password reset request audit records"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique reset request identifier",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User requesting the password reset",
    )

    token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="SHA-256 hash of the password reset JWT for lookup",
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this reset token has been used",
    )

    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the password was actually reset",
    )

    used_by_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address that performed the reset",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this reset token expires",
    )

    @property
    def is_expired(self) -> bool:
        """Check if the reset window has passed."""
        import datetime as dt_module
        return dt_module.datetime.now(dt_module.timezone.utc) > self.expires_at

    def mark_used(self, ip_address: Optional[str]) -> None:
        """Mark this token as used after a successful reset."""
        import datetime as dt_module
        self.is_used = True
        self.used_at = dt_module.datetime.now(dt_module.timezone.utc)
        self.used_by_ip = ip_address

    def __repr__(self) -> str:
        return (
            f"<PasswordResetToken id={self.id} user_id={self.user_id} "
            f"used={self.is_used}>"
        )
