"""
PromptVersion model — tracks versions of AI prompt templates.

Prompts are stored as Markdown files but their content and version
metadata are recorded here for audit trail and rollback support.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PromptVersion(Base, TimestampMixin):
    """Versioned record of an AI prompt template."""

    __tablename__ = "prompt_versions"

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_prompt_name_version"),
        {"comment": "Versioned AI prompt templates"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="Prompt name (summarize, entities, relationships, timeline, report)",
    )

    version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0.0",
        comment="Semantic version of the prompt",
    )

    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Full prompt template content",
    )

    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Human-readable description of this prompt",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="Whether this version is currently active",
    )

    def __repr__(self) -> str:
        return f"<PromptVersion name={self.name} v{self.version} active={self.is_active}>"
