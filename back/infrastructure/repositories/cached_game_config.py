from __future__ import annotations

from typing import Optional

from domain.game_night.models.game_config import GameConfig
from domain.game_night.repositories.game_config_repository import GameConfigRepository


class CachedGameConfigRepository(GameConfigRepository):
    """Garde l'agrégat courant en mémoire : seules les écritures touchent la base.

    Valable car l'API tourne en un seul processus (verrou de mutation et hub WebSocket sont déjà en mémoire).
    """

    def __init__(self, inner: GameConfigRepository) -> None:
        self._inner = inner
        self._current: Optional[GameConfig] = None

    async def get_current(self) -> GameConfig:
        if self._current is None:
            self._current = await self._inner.get_current()
        return self._current

    async def save(self, game_config: GameConfig) -> GameConfig:
        self._current = await self._inner.save(game_config)
        return self._current

    def clear(self) -> None:
        self._current = None
