from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base
from infrastructure.database.models.shared.json_document import JsonDocument


class GameNightModel(Base):
    """Une soirée : sa configuration et le cycle de vie commun des manches. L'état de chaque jeu est dans sa table."""

    __tablename__ = "game_nights"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # version, +1 à chaque écriture
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    # Configuration de la soirée (équipes, jeux, manches prévues).
    settings: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False)
    games: Mapped[list[Any]] = mapped_column(JsonDocument, nullable=False)
    rounds: Mapped[list[Any]] = mapped_column(JsonDocument, nullable=False)
    # Cycle de vie commun de la session (champs de `GameSession` hors états de jeu).
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
