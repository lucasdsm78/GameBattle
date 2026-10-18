from __future__ import annotations

from application.game_config.command_bus import HARDWARE_ONLY, SYSTEM_ONLY, CommandContext, CommandSpec
from application.game_config.game_config_models import GameConfigUpsertModel, TeamCommand
from domain.game_config.model.game_config import GameConfig

EXPIRE_DEADLINES = "system.expire-deadlines"
HARDWARE_BUZZER = "hardware.buzzer"


async def _validate_and_launch(config: GameConfig, command: GameConfigUpsertModel, context: CommandContext) -> GameConfig:
    return await context.playlists.autoimport(command.to_domain().with_timestamp().start_session())


SESSION_COMMANDS = (
    CommandSpec("game.config.replace", lambda config, command, _: command.to_domain().with_timestamp(), GameConfigUpsertModel),
    CommandSpec("game.config.validate-and-launch", _validate_and_launch, GameConfigUpsertModel),
    CommandSpec("game.config.launch", lambda config, _, context: context.playlists.autoimport(config.start_session())),
    CommandSpec("game.next-manche", lambda config, _, context: context.playlists.autoimport(config.next_manche())),
    CommandSpec("ranking.reveal-next", lambda config, *_: config.reveal_next_ranking()),
    CommandSpec(
        HARDWARE_BUZZER,
        lambda config, command, context: config.register_active_game_buzzer(command.team, context.now_ms),
        TeamCommand,
        HARDWARE_ONLY,
    ),
    CommandSpec(EXPIRE_DEADLINES, lambda config, _, context: config.expire_due_deadline(context.now_ms), roles=SYSTEM_ONLY),
)
