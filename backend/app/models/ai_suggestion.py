"""
AISuggestion model — AI-generated suggestions pending human review.

Every suggestion requires explicit investigator approval before it is
persisted to the investigation. This enforces the human-in-the-loop
workflow mandated by the AI Intelligence Engine.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SuggestionType(str, enum.Enum):
    """Types of AI-generated suggestions."""

    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    TIMELINE_EVENT = "timeline_event"
    FINDING = "finding"
    RECOMMENDATION = "recommendation"


class SuggestionStatus(str, enum.Enum):
    """Review lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AISuggestion(Base, TimestampMixin):
    """An AI-generated suggestion awaiting investigator review."""

    __tablename__ = "ai_suggestions"

    __table_args__ = ({"comment": "AI-generated suggestions pending human review"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    investigation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    suggestion_type: Mapped[SuggestionType] = mapped_column(
        Enum(SuggestionType, name="suggestion_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
        comment="Type of suggestion",
    )

    data: Mapped[dict] = mapped_column(
        JSON, nullable=False, comment="Structured suggestion payload"
    )

    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, name="suggestion_status", values_callable=lambda x: [e.value for e in x]),
        default=SuggestionStatus.PENDING,
        nullable=False,
        index=True,
        comment="Review status",
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When the review decision was made"
    )

    review_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional notes from the reviewer"
    )

    def approve(self, reviewer_id: uuid.UUID, notes: str | None = None) -> None:
        """Approve this suggestion."""
        self.status = SuggestionStatus.APPROVED
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.now(UTC)
        self.review_notes = notes

    def reject(self, reviewer_id: uuid.UUID, notes: str | None = None) -> None:
        """Reject this suggestion."""
        self.status = SuggestionStatus.REJECTED
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.now(UTC)
        self.review_notes = notes

    def __repr__(self) -> str:
        return f"<AISuggestion id={self.id} type={self.suggestion_type.value} status={self.status.value}>"
