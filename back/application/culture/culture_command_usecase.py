from __future__ import annotations

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import (
    BlindtestAnswerCommandModel,
    BlindtestBuzzerCommandModel,
    CultureDifficultyCommandModel,
    GameConfigReadModel,
)


class CultureCommandUseCase(GameConfigCommandBase):
    async def start(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_culture())

    async def select_difficulty(self, payload: CultureDifficultyCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.select_culture_difficulty(payload.difficulty))

    async def register_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.register_culture_buzzer(payload.team.strip()))

    async def answer(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.answer_culture(payload.is_correct))

    async def next_question(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.next_culture_question())
