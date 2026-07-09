"""
EchoTrace AI — Initial Database Migration

Creates the foundational schema. Currently empty — migrations will be
generated as models are added.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-09
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the initial migration."""
    # No models yet — migrations will be added as features are built
    pass


def downgrade() -> None:
    """Revert the initial migration."""
    pass
