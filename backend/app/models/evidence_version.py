"""Evidence version tracking."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class EvidenceVersion(Base, TimestampMixin):
    __tablename__ = "evidence_versions"

    __table_args__ = ({"comment": "Version history for evidence items"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    original_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stored_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sha1_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    md5_hash: Mapped[str | None] = mapped_column(String(32), nullable=True)

    change_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    evidence: Mapped[Evidence] = relationship(back_populates="versions")

    def __repr__(self) -> str:
        return f"<EvidenceVersion id={self.id} ev={self.evidence_id} v{self.version_number}>"
