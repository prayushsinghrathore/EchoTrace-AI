"""
Create AI Intelligence Engine tables.

Creates: ai_jobs, ai_suggestions, prompt_versions

Revision ID: 007_add_ai_engine_tables
Revises: 006_add_investigation_tables
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "007_add_ai_engine_tables"
down_revision: str | None = "006_add_investigation_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create AI engine tables."""

    # ── ai_jobs ───────────────────────────────────────────────────────────
    op.create_table(
        "ai_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_type", sa.Enum("SUMMARIZE", "EXTRACT_ENTITIES", "SUGGEST_RELATIONSHIPS", "GENERATE_TIMELINE", "GENERATE_REPORT", name="ai_job_type"), nullable=False),
        sa.Column("status", sa.Enum("QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="ai_job_status"), nullable=False, server_default=sa.text("'QUEUED'"), index=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("evidence_ids", postgresql.JSON, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("cost", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("cached", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("result", postgresql.JSON, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table_comment("ai_jobs", "Asynchronous AI processing jobs", existing_comment=None)

    # ── ai_suggestions ────────────────────────────────────────────────────
    op.create_table(
        "ai_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("suggestion_type", sa.Enum("ENTITY", "RELATIONSHIP", "TIMELINE_EVENT", "FINDING", "RECOMMENDATION", name="suggestion_type"), nullable=False, index=True),
        sa.Column("data", postgresql.JSON, nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="suggestion_status"), nullable=False, server_default=sa.text("'PENDING'"), index=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_table_comment("ai_suggestions", "AI-generated suggestions pending human review", existing_comment=None)

    # ── prompt_versions ───────────────────────────────────────────────────
    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, index=True),
        sa.Column("version", sa.String(20), nullable=False, server_default=sa.text("'1.0.0'")),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_prompt_name_version"),
    )
    op.create_table_comment("prompt_versions", "Versioned AI prompt templates", existing_comment=None)


def downgrade() -> None:
    """Drop AI engine tables."""
    op.drop_table("prompt_versions")
    op.drop_table("ai_suggestions")
    op.drop_table("ai_jobs")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS ai_job_type")
    op.execute("DROP TYPE IF EXISTS ai_job_status")
    op.execute("DROP TYPE IF EXISTS suggestion_type")
    op.execute("DROP TYPE IF EXISTS suggestion_status")
