"""
Organization model — top-level tenant entity.

An organization owns workspaces and is the root of the multi-tenant hierarchy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.workspace import Workspace

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    """Top-level tenant entity. Each organization is fully isolated."""

    __tablename__ = "organizations"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_organizations_slug"),
        {"comment": "Top-level tenant organizations"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name of the organization",
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
        comment="URL-friendly unique slug",
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who owns this organization",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the organization",
    )

    # Relationships
    workspaces: Mapped[list[Workspace]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} name={self.name} slug={self.slug}>"
