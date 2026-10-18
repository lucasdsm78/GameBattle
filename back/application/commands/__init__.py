from application.commands.auction import AUCTION_COMMANDS
from application.commands.blindtest import BLINDTEST_COMMANDS
from application.commands.bombe import BOMBE_COMMANDS
from application.commands.bus import CommandSpec
from application.commands.culture import CULTURE_COMMANDS
from application.commands.forbidden_word import FORBIDDEN_WORD_COMMANDS
from application.commands.memory import MEMORY_COMMANDS
from application.commands.session import (
    EXPIRE_DEADLINES,
    HARDWARE_BUZZER,
    SESSION_COMMANDS,
)
from application.commands.seven_differences import SEVEN_DIFFERENCES_COMMANDS
from application.commands.stopchrono import STOPCHRONO_COMMANDS

ALL_COMMANDS: tuple[CommandSpec, ...] = (
    *SESSION_COMMANDS,
    *BLINDTEST_COMMANDS,
    *STOPCHRONO_COMMANDS,
    *CULTURE_COMMANDS,
    *BOMBE_COMMANDS,
    *MEMORY_COMMANDS,
    *SEVEN_DIFFERENCES_COMMANDS,
    *AUCTION_COMMANDS,
    *FORBIDDEN_WORD_COMMANDS,
)

__all__ = ["ALL_COMMANDS", "EXPIRE_DEADLINES", "HARDWARE_BUZZER"]
