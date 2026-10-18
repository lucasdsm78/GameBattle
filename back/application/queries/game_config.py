from __future__ import annotations

from application.services.snapshot import GameConfigSnapshot
from application.services.unit_of_work import UnitOfWork


class GameConfigQueryService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get_current(self) -> GameConfigSnapshot:
        # Lecture dans la même unité de travail exclusive : l'instantané ne peut pas être doublé par une écriture.
        async with self._uow as uow:
            return GameConfigSnapshot.from_domain(await uow.game_configs.get_current())
