from __future__ import annotations

from infrastructure.database.models.auction.auction_game_model import AuctionGameModel
from infrastructure.database.models.blindtest.blindtest_game_model import (
    BlindtestGameModel,
)
from infrastructure.database.models.bombe.bombe_game_model import BombeGameModel
from infrastructure.database.models.culture.culture_game_model import CultureGameModel
from infrastructure.database.models.fair_price.fair_price_game_model import (
    FairPriceGameModel,
)
from infrastructure.database.models.flash_calc.flash_calc_game_model import (
    FlashCalcGameModel,
)
from infrastructure.database.models.forbidden_word.forbidden_word_game_model import (
    ForbiddenWordGameModel,
)
from infrastructure.database.models.golden_family.golden_family_game_model import (
    GoldenFamilyGameModel,
)
from infrastructure.database.models.memory.memory_game_model import MemoryGameModel
from infrastructure.database.models.right_flag.right_flag_game_model import (
    RightFlagGameModel,
)
from infrastructure.database.models.seven_differences.seven_differences_game_model import (
    SevenDifferencesGameModel,
)
from infrastructure.database.models.shared.game_state_columns import GameStateColumns
from infrastructure.database.models.stopchrono.stopchrono_game_model import (
    StopchronoGameModel,
)
from infrastructure.database.models.vanishing_word.vanishing_word_game_model import (
    VanishingWordGameModel,
)

# La soirée compose tous les jeux (comme `GameSession` dans le domaine) : c'est le seul module qui connaît
# les tables de chaque jeu. Un jeu, lui, ne connaît que la sienne.
GAME_STATE_TABLES: dict[str, type[GameStateColumns]] = {
    "blindtest": BlindtestGameModel,
    "stopchrono": StopchronoGameModel,
    "culture": CultureGameModel,
    "bombe": BombeGameModel,
    "memory": MemoryGameModel,
    "seven_differences": SevenDifferencesGameModel,
    "auction": AuctionGameModel,
    "forbidden_word": ForbiddenWordGameModel,
    "vanishing_word": VanishingWordGameModel,
    "flash_calc": FlashCalcGameModel,
    "right_flag": RightFlagGameModel,
    "golden_family": GoldenFamilyGameModel,
    "fair_price": FairPriceGameModel,
}
