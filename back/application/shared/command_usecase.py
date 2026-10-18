from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import isawaitable
from typing import Protocol

from application.blindtest.playlist_service import BlindtestPlaylistService
from application.shared.snapshot import GameConfigSnapshot
from application.shared.unit_of_work import UnitOfWork
from domain.models.game_config import GameConfig


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
    """Base des use cases d'écriture : transition de l'agrégat dans une unité de travail, puis diffusion.

    Une transition sans effet (l'agrégat renvoie `self`) n'écrit ni ne diffuse rien : on renvoie `None`.
    Les événements de domaine ne sont publiés qu'après une écriture réussie.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        publisher: SnapshotPublisher,
        playlists: BlindtestPlaylistService,
        clock: Callable[[], int] = wall_clock_ms,
    ) -> None:
        self._uow = uow
        self._publisher = publisher
        self._playlists = playlists
        self._clock = clock

    async def _execute(self, transition: Transition) -> GameConfigSnapshot | None:
        async with self._uow as uow:
            current = await uow.game_configs.get_current()
            result = transition(current, CommandContext(now_ms=self._clock(), playlists=self._playlists))
            updated = await result if isawaitable(result) else result
            if updated is current:
                return None
            updated.validate()
            uow.add(updated)
            saved, events = await uow.commit()
            # Publication encore sous le verrou (non bloquante) : les clients reçoivent les états dans l'ordre.
            snapshot = GameConfigSnapshot.from_domain(saved, events)
            self._publisher.publish(snapshot)
        return snapshot
