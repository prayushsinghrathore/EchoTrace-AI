"""
Refresh token model for rotation and revocation tracking.

Each refresh token is stored in the database so it can be:
- Rotated (old token revoked when a new one is issued)
- Revoked (explicit logout or admin action)
- Audited (track when/where tokens were issued)
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RefreshToken(Base, TimestampMixin):
    """
    Persisted refresh token for rotation and revocation.

    Each row represents one refresh token. When a token is rotated,
    the old row is marked as revoked and a new row is inserted.
    """

    __tablename__ = "refresh_tokens"

    __table_args__ = (
        {"comment": "Stored refresh tokens for rotation and revocation"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique token record identifier",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The user this token belongs to",
    )

    # The jti (JWT ID) from the token — used for lookup
    token_jti: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique JWT ID (jti claim) for this refresh token",
    )

    # Token hash (full JWT hash) for verification
    token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="HMAC-SHA256 hash of the full refresh token string",
    )

    # Rotation chain — the previous token this one rotated from
    rotated_from_jti: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="JWT ID of the token this one rotated from (null for initial tokens)",
    )

    # Revocation tracking
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this token has been revoked",
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this token was revoked",
    )

    revoked_by_action: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        comment="Action that caused revocation: rotation, logout, admin_revoke",
    )

    # Metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address that issued this token",
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="User agent that issued this token",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this token naturally expires",
    )

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        import datetime as dt_module
        return dt_module.datetime.now(self.expires_at.tzinfo) > self.expires_at

    def revoke(self, action: str = "logout") -> None:
        """Mark this token as revoked."""
        self.is_revoked = True
        self.revoked_at = func.now()
        self.revoked_by_action = action

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} user_id={self.user_id} "
            f"revoked={self.is_revoked}>"
        )
