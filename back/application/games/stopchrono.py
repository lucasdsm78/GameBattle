from __future__ import annotations

from application.game_config.command_bus import CONTROLLER_AND_DISPLAY, CommandSpec

STOPCHRONO_COMMANDS = (
    CommandSpec("stopchrono.start", lambda config, _, context: config.start_chrono(context.now_ms), roles=CONTROLLER_AND_DISPLAY),
    CommandSpec("stopchrono.stop", lambda config, _, context: config.stop_chrono(context.now_ms), roles=CONTROLLER_AND_DISPLAY),
    CommandSpec("stopchrono.next-team", lambda config, *_: config.next_chrono_team()),
)
