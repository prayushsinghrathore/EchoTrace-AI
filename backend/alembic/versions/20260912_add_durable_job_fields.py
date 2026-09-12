"""Add durable worker lease and retry fields to background jobs."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "012_add_durable_job_fields"
down_revision: str | None = "011_add_composite_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("ai_jobs", "export_jobs"):
        op.add_column(table, sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
        op.add_column(table, sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
        op.add_column(table, sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("locked_by", sa.String(length=128), nullable=True))
        op.create_index(f"ix_{table}_available_at", table, ["available_at"])
        op.create_index(f"ix_{table}_queue_claim", table, ["status", "available_at"])
    op.add_column("ai_jobs", sa.Column("options", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_jobs", "options")
    for table in ("export_jobs", "ai_jobs"):
        op.drop_index(f"ix_{table}_queue_claim", table_name=table)
        op.drop_index(f"ix_{table}_available_at", table_name=table)
        for column in ("locked_by", "locked_at", "available_at", "max_attempts", "attempts"):
            op.drop_column(table, column)
