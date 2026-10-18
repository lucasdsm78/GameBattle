from application.game_config.command_bus import CommandSpec
from application.games.auction import AUCTION_COMMANDS
from application.games.blindtest import BLINDTEST_COMMANDS
from application.games.bombe import BOMBE_COMMANDS
from application.games.culture import CULTURE_COMMANDS
from application.games.forbidden_word import FORBIDDEN_WORD_COMMANDS
from application.games.memory import MEMORY_COMMANDS
from application.games.session import EXPIRE_DEADLINES, HARDWARE_BUZZER, SESSION_COMMANDS
from application.games.seven_differences import SEVEN_DIFFERENCES_COMMANDS
from application.games.stopchrono import STOPCHRONO_COMMANDS

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
