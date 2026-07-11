"""
Add composite indexes for common query patterns.

Creates covering indexes for the most frequent query patterns identified
during Stage 11 performance audit. Composite indexes reduce index lookups
for multi-column WHERE + ORDER BY queries.

Patterns covered:
  - Evidence list by project (project_id + created_at)
  - Evidence list by workspace (workspace_id + created_at)
  - Investigation list by workspace (workspace_id + created_at)
  - Evidence tag lookups (evidence_id + tag)
  - AI job listings by workspace (workspace_id + created_at)

Revision ID: 011_add_composite_indexes
Revises: 010_add_performance_indexes
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "011_add_composite_indexes"
down_revision: str | None = "010_add_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Evidence ───────────────────────────────────────────────────────────
    # Used by: list_for_project() sorted by created_at
    op.create_index(
        "ix_evidence_project_created",
        "evidence",
        ["project_id", "created_at"],
        postgresql_concurrently=False,
    )

    # Used by: search() with workspace filter sorted by created_at
    op.create_index(
        "ix_evidence_workspace_created",
        "evidence",
        ["workspace_id", "created_at"],
        postgresql_concurrently=False,
    )

    # ── Investigations ─────────────────────────────────────────────────────
    # Used by: list_for_workspace() sorted by created_at
    op.create_index(
        "ix_investigations_workspace_created",
        "investigations",
        ["workspace_id", "created_at"],
        postgresql_concurrently=False,
    )

    # ── Evidence Tags ──────────────────────────────────────────────────────
    # Used by: _batch_load_tags() with evidence_id IN clause
    op.create_index(
        "ix_evidence_tags_eid_tag",
        "evidence_tags",
        ["evidence_id", "tag"],
        postgresql_concurrently=False,
    )

    # ── AI Jobs ────────────────────────────────────────────────────────────
    # Used by: list_jobs() in workspace sorted by created_at
    op.create_index(
        "ix_ai_jobs_workspace_created",
        "ai_jobs",
        ["workspace_id", "created_at"],
        postgresql_concurrently=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_jobs_workspace_created", table_name="ai_jobs")
    op.drop_index("ix_evidence_tags_eid_tag", table_name="evidence_tags")
    op.drop_index("ix_investigations_workspace_created", table_name="investigations")
    op.drop_index("ix_evidence_workspace_created", table_name="evidence")
    op.drop_index("ix_evidence_project_created", table_name="evidence")
