"""
Create audit log table for enterprise audit trail.

Creates: audit_logs

Revision ID: 009_add_audit_log_table
Revises: 008_add_reporting_tables
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009_add_audit_log_table"
down_revision: str | None = "008_add_reporting_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.Enum(
            "LOGIN", "LOGOUT", "LOGIN_FAILED",
            "WORKSPACE_CREATED", "WORKSPACE_UPDATED", "WORKSPACE_DELETED",
            "EVIDENCE_CREATED", "EVIDENCE_UPLOADED", "EVIDENCE_VERIFIED", "EVIDENCE_DELETED",
            "INVESTIGATION_CREATED", "INVESTIGATION_UPDATED", "INVESTIGATION_CLOSED",
            "AI_JOB_COMPLETED", "EXPORT_CREATED", "EXPORT_DOWNLOADED", "REPORT_GENERATED",
            "ENTITY_APPROVED", "ENTITY_REJECTED", "RELATIONSHIP_APPROVED", "RELATIONSHIP_REJECTED",
            "MEMBER_ADDED", "MEMBER_REMOVED", "MEMBER_ROLE_CHANGED",
            "ROLE_CHANGED", "PERMISSION_CHANGED", "PASSWORD_CHANGED", "PASSWORD_RESET",
            name="audit_action",
        ), nullable=False, index=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("metadata_json", postgresql.JSON, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
    )
    op.create_table_comment("audit_logs", "Immutable enterprise audit trail", existing_comment=None)

    op.create_index("ix_audit_logs_workspace_action", "audit_logs", ["workspace_id", "action"])
    op.create_index("ix_audit_logs_user_timestamp", "audit_logs", ["user_id", "timestamp"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.execute("DROP TYPE IF EXISTS audit_action")
