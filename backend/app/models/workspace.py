"""
Workspace model — collaborative unit within an organization.

Workspaces contain projects and have their own membership.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Workspace(Base, TimestampMixin):
    """A collaborative workspace within an organization."""

    __tablename__ = "workspaces"

    __table_args__ = (
        UniqueConstraint("slug", "organization_id", name="uq_workspace_org_slug"),
        {"comment": "Workspaces within organizations"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name of the workspace",
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="URL-friendly slug within the organization",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the workspace",
    )

    # Relationships
    organization: Mapped[Organization] = relationship(
        back_populates="workspaces",
    )

    projects: Mapped[list[Project]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    members: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    invitations: Mapped[list[Invitation]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} name={self.name} org={self.organization_id}>"
