"""Salons en ligne (`rooms`, `room_members`) et outbox transactionnelle (`outbox_events`).

Révision : 0006
Précédente : 0005
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonDocument = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=16), nullable=False, unique=True),
        sa.Column("visibility", sa.String(length=10), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("teams", JsonDocument, nullable=False),
        sa.Column("host_account_id", sa.String(length=36), sa.ForeignKey("player_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("updated_at_ms", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_rooms_updated_at_ms", "rooms", ["updated_at_ms"])
    op.create_table(
        "room_members",
        sa.Column("room_id", sa.String(length=36), sa.ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("player_accounts.id", ondelete="CASCADE"), primary_key=True, unique=True),
        sa.Column("pseudo", sa.String(length=20), nullable=False),
        sa.Column("team", sa.String(length=20), nullable=False),
        sa.Column("joined_at_ms", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("stream", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload", JsonDocument, nullable=False),
        sa.Column("audience", sa.String(length=36), nullable=True),
        sa.Column("occurred_at_ms", sa.BigInteger(), nullable=False),
        sa.Column("published_at_ms", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_outbox_events_published_at_ms", "outbox_events", ["published_at_ms"])


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("room_members")
    op.drop_table("rooms")
