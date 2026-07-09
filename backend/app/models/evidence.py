"""
Evidence model — core digital evidence item within a project.

Each evidence item belongs to a project and tracks hashes, metadata,
status, and links to versions, comments, tags, and custody chain.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class EvidenceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class EvidencePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    __table_args__ = (
        {"comment": "Digital evidence items within projects"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    collector_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(100), nullable=False, default="other", index=True)
    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_status"), default=EvidenceStatus.DRAFT, nullable=False, index=True
    )
    priority: Mapped[EvidencePriority] = mapped_column(
        Enum(EvidencePriority, name="evidence_priority"), default=EvidencePriority.MEDIUM, nullable=False
    )
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Hash fields
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    sha1_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    md5_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # File metadata
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    stored_filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    upload_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    current_version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    versions: Mapped[list["EvidenceVersion"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan", passive_deletes=True,
        order_by="EvidenceVersion.version_number.desc()",
    )
    comments: Mapped[list["EvidenceComment"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan", passive_deletes=True,
        order_by="EvidenceComment.created_at.desc()",
    )
    custody_events: Mapped[list["ChainOfCustodyEvent"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan", passive_deletes=True,
        order_by="ChainOfCustodyEvent.timestamp.desc()",
    )
    tags: Mapped[list["EvidenceTag"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan", passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} num={self.evidence_number} title={self.title}>"
