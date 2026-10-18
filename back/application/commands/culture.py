from __future__ import annotations

from application.commands.base import CommandUseCase
from application.commands.payloads import (
    AnswerCommand,
    CultureDifficultyCommand,
    TeamCommand,
)
from application.services.snapshot import GameConfigSnapshot


class CultureCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_culture())

    async def select_difficulty(self, command: CultureDifficultyCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.select_culture_difficulty(command.difficulty))

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_culture_buzzer(command.team))

    async def answer(self, command: AnswerCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.answer_culture(command.is_correct))

    async def next_question(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.next_culture_question())
