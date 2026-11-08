from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.json_document import JsonDocument


class GameStateColumns:
    """Colonnes de chaque table de jeu : l'état d'un jeu pour une partie, en document JSONB.

    - `schema_version` : version du format du document, mise à niveau par le mapper du jeu au chargement
      (migrations applicatives versionnées, pas des migrations Alembic) ;
    - `version` : verrou optimiste, +1 à chaque écriture ; une écriture qui ne trouve pas la version attendue
      est refusée au lieu d'écraser l'état écrit entre-temps.
    """

    session_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("game_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
