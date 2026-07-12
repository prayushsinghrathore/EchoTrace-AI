"""
Notification model — user notifications for investigations, evidence, and AI events.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    ASSIGNMENT = "assignment"
    EVIDENCE_UPLOADED = "evidence_uploaded"
    EVIDENCE_VERIFIED = "evidence_verified"
    AI_SUGGESTIONS_READY = "ai_suggestions_ready"
    AI_REVIEW_PENDING = "ai_review_pending"
    COMMENT = "comment"
    MENTION = "mention"
    REPORT_COMPLETED = "report_completed"
    EXPORT_COMPLETED = "export_completed"
    INVESTIGATION_UPDATED = "investigation_updated"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    __table_args__ = ({"comment": "User notifications"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="UUID of the related entity")
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Entity type (investigation, evidence, etc.)")

    def mark_read(self) -> None:
        from datetime import UTC
        self.is_read = True
        self.read_at = datetime.now(UTC)

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.notification_type.value} read={self.is_read}>"
