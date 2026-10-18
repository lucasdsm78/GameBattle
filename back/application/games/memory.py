from __future__ import annotations

from application.game_config.command_bus import CommandSpec

MEMORY_COMMANDS = (
    CommandSpec("memory.start", lambda config, *_: config.start_memory()),
    CommandSpec("memory.next-question", lambda config, *_: config.next_memory_question()),
    CommandSpec("memory.validate-sequence", lambda config, *_: config.validate_memory_sequence()),
    CommandSpec("memory.disqualify-team", lambda config, *_: config.disqualify_memory_team()),
)
