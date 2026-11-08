from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.models.shared.json_document import JsonDocument


class GameStateColumns:
    """Colonnes communes à chaque table de jeu : l'état d'un jeu pour une soirée, en document versionné.

    Le schéma interne de l'état appartient au module du jeu : un champ ajouté ou une règle modifiée ne demande
    aucune migration ; `schema_version` permet au module de mettre à niveau un état ancien au chargement.
    """

    night_id: Mapped[str] = mapped_column(String(50), ForeignKey("game_nights.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
