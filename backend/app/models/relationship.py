"""Relationship model — connections between entities."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.entity import Entity
    from app.models.investigation import Investigation

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RelationshipType(str, enum.Enum):
    CONNECTED_TO = "connected_to"
    OWNS = "owns"
    USES = "uses"
    SENT_TO = "sent_to"
    RECEIVED_FROM = "received_from"
    LOCATED_AT = "located_at"
    LOGGED_IN_FROM = "logged_in_from"
    DOWNLOADED = "downloaded"
    UPLOADED = "uploaded"
    COMMUNICATED_WITH = "communicated_with"
    CREATED = "created"
    VISITED = "visited"
    TRANSFERRED_TO = "transferred_to"
    CUSTOM = "custom"


class Relationship(Base, TimestampMixin):
    __tablename__ = "relationships"
    __table_args__ = ({"comment": "Relationships between entities"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type: Mapped[RelationshipType] = mapped_column(SAEnum(RelationshipType, name="relationship_type"), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    investigation: Mapped[Investigation] = relationship(back_populates="relationships")
    src_entity: Mapped[Entity] = relationship(back_populates="src_rels", foreign_keys=[source_entity_id])
    tgt_entity: Mapped[Entity] = relationship(back_populates="tgt_rels", foreign_keys=[target_entity_id])

    def __repr__(self):
        return f"<Relationship {self.relationship_type.value}: {self.source_entity_id} -> {self.target_entity_id}>"
