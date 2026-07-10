"""
AIJob model — tracks asynchronous AI processing jobs.

Each job represents a single AI operation (summarize, entity extraction,
relationship suggestion, timeline generation, or report generation)
with full observability metadata.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AIJobType(str, enum.Enum):
    """Types of AI jobs supported by the intelligence engine."""

    SUMMARIZE = "summarize"
    EXTRACT_ENTITIES = "extract_entities"
    SUGGEST_RELATIONSHIPS = "suggest_relationships"
    GENERATE_TIMELINE = "generate_timeline"
    GENERATE_REPORT = "generate_report"


class AIJobStatus(str, enum.Enum):
    """Lifecycle states for an AI job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIJob(Base, TimestampMixin):
    """An asynchronous AI processing job with full observability."""

    __tablename__ = "ai_jobs"

    __table_args__ = ({"comment": "Asynchronous AI processing jobs"},)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )

    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True
    )

    job_type: Mapped[AIJobType] = mapped_column(
        Enum(AIJobType, name="ai_job_type"),
        nullable=False,
        comment="Type of AI operation",
    )

    status: Mapped[AIJobStatus] = mapped_column(
        Enum(AIJobStatus, name="ai_job_status"),
        default=AIJobStatus.QUEUED,
        nullable=False,
        index=True,
        comment="Current job status",
    )

    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="LLM provider used (openai, openrouter, ollama, azure)"
    )

    model: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Model identifier (e.g. gpt-4o)"
    )

    evidence_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="UUIDs of evidence items processed"
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Number of input/prompt tokens"
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Number of output/completion tokens"
    )

    cost: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Estimated cost in USD"
    )

    latency_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="End-to-end processing time in milliseconds"
    )

    cached: Mapped[bool] = mapped_column(
        default=False, nullable=False, comment="Whether the result was served from cache"
    )

    error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error message if the job failed"
    )

    result: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Structured job result payload"
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When processing completed"
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When the job was cancelled"
    )

    def mark_running(self) -> None:
        """Transition to running state."""
        self.status = AIJobStatus.RUNNING

    def mark_completed(self, result: dict, input_tokens: int,
                       output_tokens: int, cost: float,
                       latency_ms: int, cached: bool = False) -> None:
        """Mark job as completed with result and metrics."""
        from datetime import UTC, datetime
        self.status = AIJobStatus.COMPLETED
        self.result = result
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost = cost
        self.latency_ms = latency_ms
        self.cached = cached
        self.completed_at = datetime.now(UTC)

    def mark_failed(self, error: str) -> None:
        """Transition to failed state."""
        from datetime import UTC, datetime
        self.status = AIJobStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(UTC)

    def mark_cancelled(self) -> None:
        """Transition to cancelled state."""
        from datetime import UTC, datetime
        self.status = AIJobStatus.CANCELLED
        self.cancelled_at = datetime.now(UTC)

    def __repr__(self) -> str:
        return f"<AIJob id={self.id} type={self.job_type.value} status={self.status.value}>"
