"""Investigation model — case within a workspace."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.evidence_link import EvidenceLink
    from app.models.relationship import Relationship
    from app.models.timeline_event import TimelineEvent

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class InvestigationStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CLOSED = "closed"
    ARCHIVED = "archived"


class InvestigationPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"
    __table_args__ = ({"comment": "Investigation cases within workspaces"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[InvestigationStatus] = mapped_column(Enum(InvestigationStatus, name="investigation_status", values_callable=lambda x: [e.value for e in x]), default=InvestigationStatus.OPEN, nullable=False, index=True)
    priority: Mapped[InvestigationPriority] = mapped_column(Enum(InvestigationPriority, name="investigation_priority", values_callable=lambda x: [e.value for e in x]), default=InvestigationPriority.MEDIUM, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    lead_investigator: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    entities: Mapped[list[Entity]] = relationship(back_populates="investigation", cascade="all, delete-orphan", passive_deletes=True)
    relationships: Mapped[list[Relationship]] = relationship(back_populates="investigation", cascade="all, delete-orphan", passive_deletes=True)
    timeline_events: Mapped[list[TimelineEvent]] = relationship(back_populates="investigation", cascade="all, delete-orphan", passive_deletes=True)
    evidence_links: Mapped[list[EvidenceLink]] = relationship(back_populates="investigation", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self):
        return f"<Investigation id={self.id} title={self.title} status={self.status.value}>"
