"""Schéma initial : état de la soirée, comptes joueurs et sessions.

Identique à ce que `create_all` créait jusqu'ici : une base existante se marque avec `alembic stamp 0001`.

Révision : 0001
Précédente :
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "game_config_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("aggregate_key", sa.String(length=50), nullable=False, unique=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
    )
    op.create_table(
        "player_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("pseudo", sa.String(length=20), nullable=False),
        sa.Column("pseudo_key", sa.String(length=40), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at_ms", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "player_sessions",
        sa.Column("token_hash", sa.String(length=64), primary_key=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("player_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at_ms", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_player_sessions_account_id", "player_sessions", ["account_id"])
    op.create_index("ix_player_sessions_expires_at_ms", "player_sessions", ["expires_at_ms"])


def downgrade() -> None:
    op.drop_table("player_sessions")
    op.drop_table("player_accounts")
    op.drop_table("game_config_state")
