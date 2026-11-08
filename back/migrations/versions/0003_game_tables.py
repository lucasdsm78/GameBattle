"""Une table commune pour la soirée (`game_nights`) et une table par jeu (`<jeu>_games`), à la place du document unique.

Les données de `game_config_state` sont recopiées puis la table est supprimée ; la descente refait le document.
Migration autonome : elle ne dépend pas du code de l'application, qui continuera d'évoluer.

Révision : 0003
Précédente : 0002
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonDocument = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
GAME_KEYS = (
    "blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word",
    "vanishing_word", "flash_calc", "right_flag", "golden_family", "fair_price",
)
# Champs communs de la session au moment de cette migration, avec leur valeur par défaut.
COMMON_SESSION_DEFAULTS: dict[str, Any] = {
    "active_round": None,
    "round_sequence": [],
    "round_index": 0,
    "total_rounds": 0,
    "manches_won": {},
    "manche_finished": False,
    "manche_winner": None,
    "final_ranking": [],
    "ranking_reveal_count": 0,
    "last_bombe_roller_index": None,
    "opening_stage": "",
    "opening_started_ms": 0,
    "opening_until_ms": 0,
}


def _game_nights_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(length=50), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("updated_at", sa.String(length=40), nullable=False),
        sa.Column("settings", JsonDocument, nullable=False),
        sa.Column("games", JsonDocument, nullable=False),
        sa.Column("rounds", JsonDocument, nullable=False),
        sa.Column("active_round", JsonDocument, nullable=True),
        sa.Column("round_sequence", JsonDocument, nullable=False),
        sa.Column("round_index", sa.Integer(), nullable=False),
        sa.Column("total_rounds", sa.Integer(), nullable=False),
        sa.Column("manches_won", JsonDocument, nullable=False),
        sa.Column("manche_finished", sa.Boolean(), nullable=False),
        sa.Column("manche_winner", sa.String(length=80), nullable=True),
        sa.Column("final_ranking", JsonDocument, nullable=False),
        sa.Column("ranking_reveal_count", sa.Integer(), nullable=False),
        sa.Column("last_bombe_roller_index", sa.Integer(), nullable=True),
        sa.Column("opening_stage", sa.String(length=10), nullable=False),
        sa.Column("opening_started_ms", sa.BigInteger(), nullable=False),
        sa.Column("opening_until_ms", sa.BigInteger(), nullable=False),
        sa.Column("session_updated_at", sa.String(length=40), nullable=False),
    ]


def _game_table_columns() -> list[sa.Column]:
    return [
        sa.Column("night_id", sa.String(length=50), sa.ForeignKey("game_nights.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("state", JsonDocument, nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
    ]


def _legacy_table() -> sa.Table:
    return sa.table(
        "game_config_state",
        sa.column("aggregate_key", sa.String),
        sa.column("payload", sa.JSON),
        sa.column("revision", sa.Integer),
        sa.column("checksum", sa.String),
        sa.column("source", sa.String),
        sa.column("notes", sa.Text),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )


def _lightweight(name: str, columns: list[sa.Column]) -> sa.TableClause:
    return sa.table(name, *(sa.column(column.name, column.type) for column in columns))


def upgrade() -> None:
    op.create_table("game_nights", *_game_nights_columns())
    for game_key in GAME_KEYS:
        op.create_table(f"{game_key}_games", *_game_table_columns())

    bind = op.get_bind()
    legacy, nights = _legacy_table(), _lightweight("game_nights", _game_nights_columns())
    games = {key: _lightweight(f"{key}_games", _game_table_columns()) for key in GAME_KEYS}
    for row in bind.execute(sa.select(legacy.c.aggregate_key, legacy.c.payload, legacy.c.revision)).all():
        payload = json.loads(row.payload) if isinstance(row.payload, str) else row.payload
        session = payload.get("session") or {}
        bind.execute(
            nights.insert().values(
                id=row.aggregate_key,
                revision=row.revision or 1,
                status=payload.get("status", "configuring"),
                updated_at=payload.get("updated_at", ""),
                settings=payload["settings"],
                games=payload.get("games", []),
                rounds=payload.get("rounds", []),
                session_updated_at=session.get("updated_at", ""),
                **{name: session.get(name, default) for name, default in COMMON_SESSION_DEFAULTS.items()},
            )
        )
        for game_key in GAME_KEYS:
            if game_key in session:
                bind.execute(games[game_key].insert().values(night_id=row.aggregate_key, state=session[game_key], schema_version=1))
    op.drop_table("game_config_state")


def downgrade() -> None:
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
    bind = op.get_bind()
    legacy, nights = _legacy_table(), _lightweight("game_nights", _game_nights_columns())
    games = {key: _lightweight(f"{key}_games", _game_table_columns()) for key in GAME_KEYS}
    for night in bind.execute(sa.select(nights)).mappings().all():
        session: dict[str, Any] = {name: night[name] for name in COMMON_SESSION_DEFAULTS}
        session["updated_at"] = night["session_updated_at"]
        for game_key, table in games.items():
            state = bind.execute(sa.select(table.c.state).where(table.c.night_id == night["id"])).scalar_one_or_none()
            if state is not None:
                session[game_key] = state
        payload = {
            "settings": night["settings"],
            "games": night["games"],
            "rounds": night["rounds"],
            "session": session,
            "status": night["status"],
            "updated_at": night["updated_at"],
        }
        bind.execute(
            legacy.insert().values(
                aggregate_key=night["id"],
                payload=payload,
                revision=night["revision"],
                checksum=hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(),
                source="migration",
                notes="",
                updated_at=datetime.now(timezone.utc),
            )
        )
    for game_key in GAME_KEYS:
        op.drop_table(f"{game_key}_games")
    op.drop_table("game_nights")
