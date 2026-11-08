"""Contraintes renommées après `game_nights` → `game_sessions` (PostgreSQL).

PostgreSQL ne renomme pas les contraintes avec leur table ou leur colonne : après 0004, une base migrée garde
`game_nights_pkey` et `<jeu>_games_night_id_fkey`, alors qu'une base créée depuis les modèles a
`game_sessions_pkey` et `<jeu>_games_session_id_fkey`. On aligne les noms pour qu'une future migration qui cite
une contrainte fonctionne partout. Idempotente : seul un nom encore ancien est renommé. Sans effet sur SQLite,
dont les tables ont été recréées par 0004.

Révision : 0005
Précédente : 0004
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GAME_KEYS = (
    "blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word",
    "vanishing_word", "flash_calc", "right_flag", "golden_family", "fair_price",
)


def _renames() -> list[tuple[str, str, str]]:
    return [("game_sessions", "game_nights_pkey", "game_sessions_pkey")] + [
        (f"{key}_games", f"{key}_games_night_id_fkey", f"{key}_games_session_id_fkey") for key in GAME_KEYS
    ]


def _rename_constraint(table: str, old: str, new: str) -> None:
    # Noms fixés dans ce fichier (aucune donnée extérieure) : l'interpolation est sûre.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{old}' AND conrelid = '{table}'::regclass) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, old, new in _renames():
        _rename_constraint(table, old, new)


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table, old, new in _renames():
        _rename_constraint(table, new, old)
