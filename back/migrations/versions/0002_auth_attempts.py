"""Compteurs d'essais de connexion et d'inscription, persistés et partagés entre processus.

Révision : 0002
Précédente : 0001
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_attempts",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("window_start_ms", sa.BigInteger(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_auth_attempts_window_start_ms", "auth_attempts", ["window_start_ms"])


def downgrade() -> None:
    op.drop_table("auth_attempts")
