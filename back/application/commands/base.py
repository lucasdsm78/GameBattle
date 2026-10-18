from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import isawaitable
from typing import Protocol

from application.services.playlist import BlindtestPlaylistService
from application.services.snapshot import GameConfigSnapshot
from domain.models.game_config import GameConfig
from domain.repositories.game_config import GameConfigRepository


def wall_clock_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True, slots=True)
class CommandContext:
    now_ms: int
    playlists: BlindtestPlaylistService


Transition = Callable[[GameConfig, CommandContext], GameConfig | Awaitable[GameConfig]]


class SnapshotPublisher(Protocol):
    def publish(self, snapshot: GameConfigSnapshot) -> None:
        """Diffuse sans attendre : appelé sous le verrou de mutation pour garantir l'ordre des états."""


class CommandUseCase:
    """Base des use cases d'écriture : applique une transition de l'agrégat, persiste puis diffuse.

    Une transition sans effet (l'agrégat renvoie `self`) n'écrit ni ne diffuse rien : on renvoie `None`.
    """

    def __init__(
        self,
        repository: GameConfigRepository,
        publisher: SnapshotPublisher,
        playlists: BlindtestPlaylistService,
        clock: Callable[[], int] = wall_clock_ms,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._playlists = playlists
        self._clock = clock

    async def _execute(self, transition: Transition) -> GameConfigSnapshot | None:
        async with self._repository.mutation_lock:
            current = await self._repository.get_current()
            result = transition(current, CommandContext(now_ms=self._clock(), playlists=self._playlists))
            updated = await result if isawaitable(result) else result
            if updated is current:
                return None
            updated.validate()
            await self._repository.save(updated)
            snapshot = GameConfigSnapshot.from_domain(updated)
            self._publisher.publish(snapshot)
        return snapshot
