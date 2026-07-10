"""
Create Stage 7 reporting, notification, activity, and export tables.

Creates: notifications, activity_events, export_jobs

Revision ID: 008_add_reporting_tables
Revises: 007_add_ai_engine_tables
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "008_add_reporting_tables"
down_revision: str | None = "007_add_ai_engine_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── notifications ─────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("notification_type", sa.Enum("ASSIGNMENT", "EVIDENCE_UPLOADED", "EVIDENCE_VERIFIED", "AI_SUGGESTIONS_READY", "AI_REVIEW_PENDING", "COMMENT", "MENTION", "REPORT_COMPLETED", "EXPORT_COMPLETED", "INVESTIGATION_UPDATED", name="notification_type"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("link", sa.String(1000), nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Comment("User notifications"),
    )

    # ── activity_events ──────────────────────────────────────────────────
    op.create_table(
        "activity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("event_type", sa.Enum("INVESTIGATION_CREATED", "INVESTIGATION_UPDATED", "INVESTIGATION_CLOSED", "EVIDENCE_CREATED", "EVIDENCE_UPLOADED", "EVIDENCE_VERIFIED", "EVIDENCE_DELETED", "ENTITY_CREATED", "RELATIONSHIP_CREATED", "TIMELINE_EVENT_CREATED", "COMMENT_ADDED", "MEMBER_ADDED", "MEMBER_REMOVED", "AI_JOB_COMPLETED", "REPORT_GENERATED", "EXPORT_COMPLETED", "PROJECT_CREATED", name="activity_event_type"), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata_json", postgresql.JSON, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Comment("Activity timeline events across workspaces"),
    )

    # ── export_jobs ──────────────────────────────────────────────────────
    op.create_table(
        "export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("entity_type", sa.Enum("INVESTIGATION", "EVIDENCE", "REPORT", "GRAPH", "TIMELINE", name="export_entity_type"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("format", sa.Enum("PDF", "HTML", "MARKDOWN", "JSON", "CSV", "ZIP", name="export_format"), nullable=False),
        sa.Column("status", sa.Enum("QUEUED", "RUNNING", "COMPLETED", "FAILED", "EXPIRED", name="export_job_status"), nullable=False, server_default=sa.text("'QUEUED'"), index=True),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("download_token", sa.String(128), nullable=True, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Comment("Background export jobs with download tokens"),
    )

    # Indexes
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "is_read"])
    op.create_index("ix_activity_events_workspace_occurred", "activity_events", ["workspace_id", "occurred_at"])
    op.create_index("ix_export_jobs_workspace_status", "export_jobs", ["workspace_id", "status"])


def downgrade() -> None:
    op.drop_table("export_jobs")
    op.drop_table("activity_events")
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS activity_event_type")
    op.execute("DROP TYPE IF EXISTS export_entity_type")
    op.execute("DROP TYPE IF EXISTS export_format")
    op.execute("DROP TYPE IF EXISTS export_job_status")
