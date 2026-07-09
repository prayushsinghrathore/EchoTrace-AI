"""
Invitation model — pending workspace invitations.

Tracks invitations sent to email addresses with expiry and role.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.workspace import Workspace

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.workspace_member import WorkspaceRole


class Invitation(Base, TimestampMixin):
    """A pending invitation to join a workspace."""

    __tablename__ = "invitations"

    __table_args__ = (
        {"comment": "Pending workspace invitations"},
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

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        comment="Email address of the invited user",
    )

    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who sent the invitation",
    )

    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role"),
        default=WorkspaceRole.VIEWER,
        nullable=False,
        comment="Role to assign on acceptance",
    )

    token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique invitation token",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the invitation expires",
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the invitation was accepted",
    )

    declined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the invitation was declined",
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(
        back_populates="invitations",
    )

    @property
    def is_expired(self) -> bool:
        import datetime as dt_module
        return dt_module.datetime.now(dt_module.UTC) > self.expires_at

    @property
    def is_accepted(self) -> bool:
        return self.accepted_at is not None

    @property
    def is_declined(self) -> bool:
        return self.declined_at is not None

    def accept(self) -> None:
        import datetime as dt_module
        self.accepted_at = dt_module.datetime.now(dt_module.UTC)

    def decline(self) -> None:
        import datetime as dt_module
        self.declined_at = dt_module.datetime.now(dt_module.UTC)

    def __repr__(self) -> str:
        return f"<Invitation id={self.id} email={self.email} ws={self.workspace_id}>"
