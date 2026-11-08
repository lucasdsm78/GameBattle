from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base
from infrastructure.database.json_document import JsonDocument


class GameSessionModel(Base):
    """Une partie : le cycle de vie commun à tous les jeux, en colonnes. L'état propre de chaque jeu est dans sa table.

    `version` est le verrou optimiste de la partie : +1 à chaque écriture, refusée si la version a changé entre-temps.
    """

    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # aujourd'hui « current », demain un salon
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    active_game_key: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # jeu de la manche en cours
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default="")  # horodatage métier de l'agrégat
    # Configuration de la partie (équipes, jeux, manches prévues).
    settings: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False)
    games: Mapped[list[Any]] = mapped_column(JsonDocument, nullable=False)
    rounds: Mapped[list[Any]] = mapped_column(JsonDocument, nullable=False)
    # Cycle de vie commun (champs de `GameSession` hors états de jeu).
    active_round: Mapped[Optional[dict[str, Any]]] = mapped_column(JsonDocument, nullable=True)
    round_sequence: Mapped[list[str]] = mapped_column(JsonDocument, nullable=False)
    round_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manches_won: Mapped[dict[str, int]] = mapped_column(JsonDocument, nullable=False)
    manche_finished: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manche_winner: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    final_ranking: Mapped[list[Any]] = mapped_column(JsonDocument, nullable=False)
    ranking_reveal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_bombe_roller_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    opening_stage: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    opening_started_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    opening_until_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    session_updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default="")
