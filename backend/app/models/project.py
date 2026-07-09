"""
Project model — investigation unit within a workspace.

All evidence, timelines, AI investigations, graphs, and reports
belong to a project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.workspace import Workspace

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProjectStatus(str, enum.Enum):
    """Status of a project."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base, TimestampMixin):
    """An investigation project within a workspace."""

    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint("slug", "workspace_id", name="uq_project_ws_slug"),
        {"comment": "Investigation projects within workspaces"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name of the project",
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        comment="URL-friendly slug within the workspace",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the project",
    )

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        default=ProjectStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Current project status",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        back_populates="projects",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name} status={self.status.value}>"
