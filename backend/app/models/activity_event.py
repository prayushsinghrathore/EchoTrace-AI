"""
ActivityEvent model — workspace and investigation activity timeline.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ActivityEventType(str, enum.Enum):
    INVESTIGATION_CREATED = "investigation_created"
    INVESTIGATION_UPDATED = "investigation_updated"
    INVESTIGATION_CLOSED = "investigation_closed"
    EVIDENCE_CREATED = "evidence_created"
    EVIDENCE_UPLOADED = "evidence_uploaded"
    EVIDENCE_VERIFIED = "evidence_verified"
    EVIDENCE_DELETED = "evidence_deleted"
    ENTITY_CREATED = "entity_created"
    RELATIONSHIP_CREATED = "relationship_created"
    TIMELINE_EVENT_CREATED = "timeline_event_created"
    COMMENT_ADDED = "comment_added"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    AI_JOB_COMPLETED = "ai_job_completed"
    REPORT_GENERATED = "report_generated"
    EXPORT_COMPLETED = "export_completed"
    PROJECT_CREATED = "project_created"


class ActivityEvent(Base, TimestampMixin):
    __tablename__ = "activity_events"

    __table_args__ = ({"comment": "Activity timeline events across workspaces"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    event_type: Mapped[ActivityEventType] = mapped_column(
        Enum(ActivityEventType, name="activity_event_type"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ActivityEvent id={self.id} type={self.event_type.value}>"
