from __future__ import annotations

from application.game_config.command_bus import CONTROLLER_AND_DISPLAY, CommandSpec
from application.game_config.game_config_models import TeamCommand

BOMBE_COMMANDS = (
    CommandSpec("bombe.start", lambda config, _, context: config.start_bombe(context.now_ms)),
    CommandSpec(
        "bombe.buzzer",
        lambda config, command, context: config.register_bombe_buzzer(command.team, context.now_ms),
        TeamCommand,
        CONTROLLER_AND_DISPLAY,
    ),
    CommandSpec(
        "bombe.begin-after-roll",
        lambda config, _, context: config.begin_bombe_after_roll(context.now_ms),
        roles=CONTROLLER_AND_DISPLAY,
    ),
    CommandSpec("bombe.previous-team", lambda config, _, context: config.previous_bombe_team(context.now_ms)),
    CommandSpec("bombe.explode", lambda config, _, context: config.explode_bombe(context.now_ms), roles=CONTROLLER_AND_DISPLAY),
)
