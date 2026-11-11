"""Salons « chacun pour soi » : nombre maximum de joueurs choisi par l'hôte (`rooms.max_players`).

Révision : 0007
Précédente : 0006
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Les salons existants étaient des 1 contre 1 (2 joueurs) ; en équipes, la capacité se déduit des équipes.
    with op.batch_alter_table("rooms") as table:
        table.add_column(sa.Column("max_players", sa.Integer(), nullable=False, server_default="2"))
    rooms = sa.table("rooms", sa.column("id", sa.String), sa.column("format", sa.String), sa.column("teams", sa.JSON), sa.column("max_players", sa.Integer))
    bind = op.get_bind()
    for row in bind.execute(sa.select(rooms.c.id, rooms.c.teams).where(rooms.c.format == "teams")).all():
        teams = json.loads(row.teams) if isinstance(row.teams, str) else row.teams or []
        bind.execute(rooms.update().where(rooms.c.id == row.id).values(max_players=4 * len(teams)))  # 4 joueurs par équipe
    with op.batch_alter_table("rooms") as table:  # la valeur par défaut ne servait qu'aux lignes existantes
        table.alter_column("max_players", server_default=None, existing_type=sa.Integer(), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("rooms") as table:
        table.drop_column("max_players")
