"""
EchoTrace AI — Initial Database Migration

Creates the foundational schema. Currently empty — migrations will be
generated as models are added.

Revision ID: 001_initial
Revises:
Create Date: 2026-07-09
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the initial migration."""
    # No models yet — migrations will be added as features are built
    pass


def downgrade() -> None:
    """Revert the initial migration."""
    pass
