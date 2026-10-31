from __future__ import annotations

from application.game_night.game_night_commands import GameConfigUpsertModel
from application.shared.command_usecase import CommandUseCase
from application.shared.commands import TeamCommand
from application.shared.snapshot import GameConfigSnapshot


class GameNightCommandUseCase(CommandUseCase):
    async def replace_config(self, command: GameConfigUpsertModel) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: command.to_domain().with_timestamp())

    async def validate_and_launch(self, command: GameConfigUpsertModel) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: ctx.playlists.autoimport(command.to_domain().with_timestamp().start_session(ctx.now_ms)))

    async def launch_game(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: ctx.playlists.autoimport(config.start_session(ctx.now_ms)))

    async def next_manche(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: ctx.playlists.autoimport(config.next_manche(ctx.now_ms)))

    async def skip_opening(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.skip_opening(ctx.now_ms))

    async def reveal_next_ranking(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.reveal_next_ranking())

    async def register_hardware_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_active_game_buzzer(command.team, ctx.now_ms))

    async def expire_due_deadlines(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.expire_due_deadline(ctx.now_ms))
