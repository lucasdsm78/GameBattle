from __future__ import annotations

from application.game_config.command_bus import CommandSpec
from application.game_config.game_config_models import ForbiddenWordCardCommand

FORBIDDEN_WORD_COMMANDS = (
    CommandSpec("forbidden-word.start-turn", lambda config, _, context: config.start_forbidden_word_turn(context.now_ms)),
    CommandSpec(
        "forbidden-word.found",
        lambda config, command, context: config.resolve_forbidden_word_card(command.card_id, found=True, now_ms=context.now_ms),
        ForbiddenWordCardCommand,
    ),
    CommandSpec(
        "forbidden-word.skip",
        lambda config, command, context: config.resolve_forbidden_word_card(command.card_id, found=False, now_ms=context.now_ms),
        ForbiddenWordCardCommand,
    ),
)
