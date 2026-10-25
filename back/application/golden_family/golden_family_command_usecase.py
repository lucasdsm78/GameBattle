from __future__ import annotations

from application.golden_family.golden_family_commands import FamilyAnswerCommand, FamilyTurnCommand
from application.shared.command_usecase import CommandUseCase
from application.shared.commands import TeamCommand
from application.shared.snapshot import GameConfigSnapshot


class GoldenFamilyCommandUseCase(CommandUseCase):
    async def next_question(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.show_next_family_question())

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_golden_family_buzzer(command.team, ctx.now_ms))

    async def give_answer(self, command: FamilyAnswerCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.give_family_answer(command.answer_index, command.turn))

    async def strike(self, command: FamilyTurnCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.strike_family_answer(command.turn))

    async def reveal_board(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.reveal_family_board())
