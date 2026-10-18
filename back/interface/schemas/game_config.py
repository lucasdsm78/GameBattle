from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from application.game_night.game_night_commands import GameStatus


class GameConfigResponse(BaseModel):
    """Schéma de réponse HTTP (documentation OpenAPI) de la vue régie ou écran public."""

    settings: dict[str, Any]
    games: list[dict[str, Any]]
    rounds: list[dict[str, Any]]
    session: dict[str, Any]
    status: GameStatus
    updated_at: str
    summary: dict[str, Any]
