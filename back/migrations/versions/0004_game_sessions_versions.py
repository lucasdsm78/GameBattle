"""`game_nights` devient `game_sessions` : verrou optimiste, dates de création et d'écriture, jeu en cours.

- `game_sessions` : `revision` devient `version` (verrou optimiste), ajout de `created_at`, `saved_at` et
  `active_game_key` (tiré de la manche en cours, pour les requêtes) ;
- chaque table de jeu : `night_id` devient `session_id`, ajout de `version` (verrou optimiste de la ligne).
Les données sont conservées. Migration autonome, indépendante du code de l'application.

Révision : 0004
Précédente : 0003
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonDocument = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
GAME_KEYS = (
    "blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word",
    "vanishing_word", "flash_calc", "right_flag", "golden_family", "fair_price",
)


def upgrade() -> None:
    op.rename_table("game_nights", "game_sessions")
    with op.batch_alter_table("game_sessions") as table:
        table.alter_column("revision", new_column_name="version", existing_type=sa.Integer(), existing_nullable=False)
        table.add_column(sa.Column("active_game_key", sa.String(length=40), nullable=True))
        table.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        table.add_column(sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    bind = op.get_bind()
    sessions = sa.table("game_sessions", sa.column("id", sa.String), sa.column("active_round", JsonDocument), sa.column("active_game_key", sa.String))
    for row in bind.execute(sa.select(sessions.c.id, sessions.c.active_round)).all():
        active_round = json.loads(row.active_round) if isinstance(row.active_round, str) else row.active_round
        if active_round:
            bind.execute(sessions.update().where(sessions.c.id == row.id).values(active_game_key=active_round.get("game_key")))

    for game_key in GAME_KEYS:
        with op.batch_alter_table(f"{game_key}_games") as table:
            table.alter_column("night_id", new_column_name="session_id", existing_type=sa.String(length=50), existing_nullable=False)
            table.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    for game_key in GAME_KEYS:
        with op.batch_alter_table(f"{game_key}_games") as table:
            table.drop_column("version")
            table.alter_column("session_id", new_column_name="night_id", existing_type=sa.String(length=50), existing_nullable=False)
    with op.batch_alter_table("game_sessions") as table:
        table.drop_column("saved_at")
        table.drop_column("created_at")
        table.drop_column("active_game_key")
        table.alter_column("version", new_column_name="revision", existing_type=sa.Integer(), existing_nullable=False)
    op.rename_table("game_sessions", "game_nights")
