from __future__ import annotations

from application.game_config.command_bus import CONTROLLER_AND_DISPLAY, CommandSpec
from application.game_config.game_config_models import SevenDifferenceFoundCommand, TeamCommand

SEVEN_DIFFERENCES_COMMANDS = (
    CommandSpec("seven-differences.start", lambda config, _, context: config.start_seven_differences(context.now_ms)),
    CommandSpec(
        "seven-differences.open",
        lambda config, _, context: config.open_seven_differences(context.now_ms),
        roles=CONTROLLER_AND_DISPLAY,
    ),
    CommandSpec(
        "seven-differences.buzzer",
        lambda config, command, context: config.register_seven_differences_buzzer(command.team, context.now_ms),
        TeamCommand,
        CONTROLLER_AND_DISPLAY,
    ),
    CommandSpec(
        "seven-differences.found",
        lambda config, command, _: config.find_seven_difference(command.difference_id),
        SevenDifferenceFoundCommand,
    ),
    CommandSpec("seven-differences.reject", lambda config, *_: config.reject_seven_differences_answer()),
)
