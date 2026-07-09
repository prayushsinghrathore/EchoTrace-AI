"""Evidence tags — many-to-many via simple join table."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.evidence import Evidence

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EvidenceTag(Base):
    __tablename__ = "evidence_tags"

    __table_args__ = (
        UniqueConstraint("evidence_id", "tag", name="uq_evidence_tag"),
        {"comment": "Tags associated with evidence items"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    evidence: Mapped[Evidence] = relationship(back_populates="tags")

    def __repr__(self) -> str:
        return f"<EvidenceTag {self.tag} ev={self.evidence_id}>"
