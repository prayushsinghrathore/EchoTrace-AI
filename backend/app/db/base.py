"""
SQLAlchemy declarative base and mixins.

Provides the foundational ORM classes that all models extend.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.

    All database models inherit from this class.
    """

    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns.

    All auditable entities should inherit this mixin.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when the record was last updated",
    )


class UUIDMixin:
    """
    Mixin that adds a UUID primary key.

    Provides a UUID4-based primary key for distributed compatibility.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="UUID v4 primary key",
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft-delete capability.

    Records are marked as deleted rather than physically removed.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Timestamp when the record was soft-deleted (null = active)",
    )

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.deleted_at = datetime.now(UTC)
