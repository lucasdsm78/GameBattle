from __future__ import annotations

from application.game_config.command.base import GameConfigCommandBase
from application.blindtest.blindtest_command_usecase import BlindtestCommandUseCase
from application.game_config.game_config_models import GameConfigReadModel, GameConfigUpsertModel
from domain.game_config.repository.game_config_repository import GameConfigRepository


class SessionCommandUseCase(GameConfigCommandBase):

    def __init__(self, repository: GameConfigRepository, blindtest: BlindtestCommandUseCase) -> None:
        super().__init__(repository)
        self._blindtest = blindtest

    async def replace_config(self, payload: GameConfigUpsertModel) -> GameConfigReadModel:
        return await self._persist(payload.to_domain().with_timestamp())

    async def launch_game(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: self._blindtest.autoimport(config.start_session()))

    async def next_manche(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: self._blindtest.autoimport(config.next_manche()))

    async def reveal_next_ranking(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.reveal_next_ranking())
