"""
Create evidence management tables.

Creates: evidence, evidence_versions, evidence_tags, evidence_comments, chain_of_custody_events

Revision ID: 005_add_evidence_tables
Revises: 004_add_workspace_tables
Create Date: 2026-07-10
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "005_add_evidence_tables"
down_revision: Union[str, None] = "004_add_workspace_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Evidence ─────────────────────────────────────────────────────────
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("collector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("evidence_number", sa.String(100), nullable=False, index=True),
        sa.Column("category", sa.String(100), nullable=False, server_default="other", index=True),
        sa.Column("status", sa.Enum("draft", "pending_review", "verified", "rejected", "archived", name="evidence_status"), nullable=False, server_default="draft", index=True),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="evidence_priority"), nullable=False, server_default="medium"),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("sha256_hash", sa.String(64), nullable=True, index=True),
        sa.Column("sha1_hash", sa.String(40), nullable=True),
        sa.Column("md5_hash", sa.String(32), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("original_filename", sa.String(500), nullable=True),
        sa.Column("stored_filename", sa.String(500), nullable=True),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("upload_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_version_number", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("evidence_number", name="uq_evidence_number"),
        comment="Digital evidence items within projects",
    )

    # ── Evidence Versions ────────────────────────────────────────────────
    op.create_table(
        "evidence_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=True),
        sa.Column("stored_filename", sa.String(500), nullable=True),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=True),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column("sha1_hash", sa.String(40), nullable=True),
        sa.Column("md5_hash", sa.String(32), nullable=True),
        sa.Column("change_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        comment="Version history for evidence items",
    )

    # ── Evidence Tags ────────────────────────────────────────────────────
    op.create_table(
        "evidence_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tag", sa.String(100), nullable=False, index=True),
        sa.UniqueConstraint("evidence_id", "tag", name="uq_evidence_tag"),
        comment="Tags associated with evidence items",
    )

    # ── Evidence Comments ────────────────────────────────────────────────
    op.create_table(
        "evidence_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_edited", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        comment="Comments on evidence items",
    )

    # ── Chain of Custody Events ──────────────────────────────────────────
    op.create_table(
        "chain_of_custody_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        comment="Immutable chain of custody events",
    )
    op.create_index("ix_custody_evidence_timestamp", "chain_of_custody_events", ["evidence_id", sa.text("timestamp DESC")])


def downgrade() -> None:
    op.drop_table("chain_of_custody_events")
    op.drop_table("evidence_comments")
    op.drop_table("evidence_tags")
    op.drop_table("evidence_versions")
    op.drop_table("evidence")
    op.execute("DROP TYPE IF EXISTS evidence_status")
    op.execute("DROP TYPE IF EXISTS evidence_priority")
