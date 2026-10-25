from __future__ import annotations

from application.shared.command_usecase import CommandUseCase
from application.shared.commands import AnswerCommand, TeamCommand
from application.shared.snapshot import GameConfigSnapshot


class VanishingWordCommandUseCase(CommandUseCase):
    async def start_round(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_vanishing_round(ctx.now_ms))

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_vanishing_buzzer(command.team, ctx.now_ms))

    async def answer(self, command: AnswerCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.judge_vanishing_word(command.is_correct))

    async def reveal(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.reveal_vanishing_word())
