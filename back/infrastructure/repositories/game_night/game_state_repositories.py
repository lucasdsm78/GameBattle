from __future__ import annotations

from infrastructure.database.games.auction.auction_repository import AuctionRepository
from infrastructure.database.games.blindtest.blindtest_repository import (
    BlindtestRepository,
)
from infrastructure.database.games.bombe.bombe_repository import BombeRepository
from infrastructure.database.games.culture.culture_repository import CultureRepository
from infrastructure.database.games.fair_price.fair_price_repository import (
    FairPriceRepository,
)
from infrastructure.database.games.flash_calc.flash_calc_repository import (
    FlashCalcRepository,
)
from infrastructure.database.games.forbidden_word.forbidden_word_repository import (
    ForbiddenWordRepository,
)
from infrastructure.database.games.golden_family.golden_family_repository import (
    GoldenFamilyRepository,
)
from infrastructure.database.games.memory.memory_repository import MemoryRepository
from infrastructure.database.games.right_flag.right_flag_repository import (
    RightFlagRepository,
)
from infrastructure.database.games.seven_differences.seven_differences_repository import (
    SevenDifferencesRepository,
)
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)
from infrastructure.database.games.stopchrono.stopchrono_repository import (
    StopchronoRepository,
)
from infrastructure.database.games.vanishing_word.vanishing_word_repository import (
    VanishingWordRepository,
)

# La partie compose tous les jeux (comme `GameSession` dans le domaine) : c'est le seul module qui connaît le
# dépôt de chaque jeu. Un jeu, lui, ne connaît que le sien.
GAME_STATE_REPOSITORIES: dict[str, GameStateRepository] = {
    "blindtest": BlindtestRepository(),
    "stopchrono": StopchronoRepository(),
    "culture": CultureRepository(),
    "bombe": BombeRepository(),
    "memory": MemoryRepository(),
    "seven_differences": SevenDifferencesRepository(),
    "auction": AuctionRepository(),
    "forbidden_word": ForbiddenWordRepository(),
    "vanishing_word": VanishingWordRepository(),
    "flash_calc": FlashCalcRepository(),
    "right_flag": RightFlagRepository(),
    "golden_family": GoldenFamilyRepository(),
    "fair_price": FairPriceRepository(),
}
