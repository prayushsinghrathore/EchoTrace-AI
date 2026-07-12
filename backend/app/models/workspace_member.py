"""
WorkspaceMember model — user membership within a workspace with role.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WorkspaceRole(str, enum.Enum):
    """Roles within a workspace."""

    OWNER = "owner"
    ADMIN = "admin"
    INVESTIGATOR = "investigator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class WorkspaceMember(Base):
    """Many-to-many relationship between users and workspaces with role."""

    __tablename__ = "workspace_members"

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
        {"comment": "User membership in workspaces with role"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role", values_callable=lambda x: [e.value for e in x]),
        default=WorkspaceRole.VIEWER,
        nullable=False,
        comment="Role within the workspace",
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the user joined the workspace",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        back_populates="members",
    )

    user: Mapped[User] = relationship(
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<WorkspaceMember user={self.user_id} ws={self.workspace_id} role={self.role.value}>"
