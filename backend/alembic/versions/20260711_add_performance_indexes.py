"""
Add performance indexes for common query patterns.

Creates indexes on foreign keys and frequently filtered columns that
were missing from the initial schema. These indexes improve query
performance for evidence lookups, investigation filtering, audit
trails, and notification queries.

Revision ID: 010_add_performance_indexes
Revises: 009_add_audit_log_table
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "010_add_performance_indexes"
down_revision: str | None = "009_add_audit_log_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Evidence ───────────────────────────────────────────────────────────
    # created_by / updated_by are frequently used for ownership queries
    op.create_index("ix_evidence_created_by", "evidence", ["created_by"], postgresql_concurrently=False)
    op.create_index("ix_evidence_updated_by", "evidence", ["updated_by"], postgresql_concurrently=False)

    # Composite index for workspace-scoped evidence listings
    op.create_index(
        "ix_evidence_workspace_status",
        "evidence",
        ["workspace_id", "status"],
        postgresql_concurrently=False,
    )

    # ── Investigations ─────────────────────────────────────────────────────
    # Ownership and assignment lookups
    op.create_index("ix_investigations_created_by", "investigations", ["created_by"], postgresql_concurrently=False)
    op.create_index(
        "ix_investigations_lead_investigator",
        "investigations",
        ["lead_investigator"],
        postgresql_concurrently=False,
    )

    # ── Entities ───────────────────────────────────────────────────────────
    op.create_index("ix_entities_created_by", "entities", ["created_by"], postgresql_concurrently=False)

    # ── Evidence Comments ──────────────────────────────────────────────────
    op.create_index("ix_evidence_comments_created_by", "evidence_comments", ["created_by"], postgresql_concurrently=False)

    # ── Chain of Custody ───────────────────────────────────────────────────
    op.create_index("ix_chain_of_custody_created_by", "chain_of_custody", ["created_by"], postgresql_concurrently=False)

    # ── Evidence Versions ──────────────────────────────────────────────────
    op.create_index("ix_evidence_versions_created_by", "evidence_versions", ["created_by"], postgresql_concurrently=False)

    # ── Invitations ────────────────────────────────────────────────────────
    op.create_index("ix_invitations_workspace_id", "invitations", ["workspace_id"], postgresql_concurrently=False)
    op.create_index("ix_invitations_invited_by", "invitations", ["invited_by"], postgresql_concurrently=False)

    # ── AI Jobs ────────────────────────────────────────────────────────────
    op.create_index("ix_ai_jobs_investigation_id", "ai_jobs", ["investigation_id"], postgresql_concurrently=False)

    # ── AI Suggestions ─────────────────────────────────────────────────────
    op.create_index("ix_ai_suggestions_created_by", "ai_suggestions", ["created_by"], postgresql_concurrently=False)


def downgrade() -> None:
    op.drop_index("ix_ai_suggestions_created_by", table_name="ai_suggestions")
    op.drop_index("ix_ai_jobs_investigation_id", table_name="ai_jobs")
    op.drop_index("ix_invitations_invited_by", table_name="invitations")
    op.drop_index("ix_invitations_workspace_id", table_name="invitations")
    op.drop_index("ix_evidence_versions_created_by", table_name="evidence_versions")
    op.drop_index("ix_chain_of_custody_created_by", table_name="chain_of_custody")
    op.drop_index("ix_evidence_comments_created_by", table_name="evidence_comments")
    op.drop_index("ix_entities_created_by", table_name="entities")
    op.drop_index("ix_investigations_lead_investigator", table_name="investigations")
    op.drop_index("ix_investigations_created_by", table_name="investigations")
    op.drop_index("ix_evidence_workspace_status", table_name="evidence")
    op.drop_index("ix_evidence_updated_by", table_name="evidence")
    op.drop_index("ix_evidence_created_by", table_name="evidence")
