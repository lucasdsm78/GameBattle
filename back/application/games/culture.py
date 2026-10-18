from __future__ import annotations

from application.game_config.command_bus import CONTROLLER_AND_DISPLAY, CommandSpec
from application.game_config.game_config_models import AnswerCommand, CultureDifficultyCommand, TeamCommand

CULTURE_COMMANDS = (
    CommandSpec("culture.start", lambda config, *_: config.start_culture()),
    CommandSpec(
        "culture.select-difficulty",
        lambda config, command, _: config.select_culture_difficulty(command.difficulty),
        CultureDifficultyCommand,
    ),
    CommandSpec(
        "culture.buzzer", lambda config, command, _: config.register_culture_buzzer(command.team), TeamCommand, CONTROLLER_AND_DISPLAY
    ),
    CommandSpec("culture.answer", lambda config, command, _: config.answer_culture(command.is_correct), AnswerCommand),
    CommandSpec("culture.next-question", lambda config, *_: config.next_culture_question()),
)
