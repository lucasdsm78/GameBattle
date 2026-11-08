"""Point d'agrégation des tables, réservé au schéma : Alembic et `Database.create_schema` l'importent avant de
lire `Base.metadata`. Ce n'est pas un point d'accès métier : le code d'un module importe ses propres modèles,
jamais ce fichier (règle vérifiée par `tests/test_architecture.py`).
"""

from infrastructure.database.accounts.auth_attempt_model import AuthAttemptModel
from infrastructure.database.accounts.player_account_model import (
    PlayerAccountModel,
)
from infrastructure.database.accounts.player_session_model import (
    PlayerSessionModel,
)
from infrastructure.database.game_sessions.game_session_model import GameSessionModel
from infrastructure.database.games.auction.auction_game_model import AuctionGameModel
from infrastructure.database.games.blindtest.blindtest_game_model import (
    BlindtestGameModel,
)
from infrastructure.database.games.bombe.bombe_game_model import BombeGameModel
from infrastructure.database.games.culture.culture_game_model import CultureGameModel
from infrastructure.database.games.fair_price.fair_price_game_model import (
    FairPriceGameModel,
)
from infrastructure.database.games.flash_calc.flash_calc_game_model import (
    FlashCalcGameModel,
)
from infrastructure.database.games.forbidden_word.forbidden_word_game_model import (
    ForbiddenWordGameModel,
)
from infrastructure.database.games.golden_family.golden_family_game_model import (
    GoldenFamilyGameModel,
)
from infrastructure.database.games.memory.memory_game_model import MemoryGameModel
from infrastructure.database.games.right_flag.right_flag_game_model import (
    RightFlagGameModel,
)
from infrastructure.database.games.seven_differences.seven_differences_game_model import (
    SevenDifferencesGameModel,
)
from infrastructure.database.games.stopchrono.stopchrono_game_model import (
    StopchronoGameModel,
)
from infrastructure.database.games.vanishing_word.vanishing_word_game_model import (
    VanishingWordGameModel,
)

__all__ = [
    "AuctionGameModel",
    "AuthAttemptModel",
    "BlindtestGameModel",
    "BombeGameModel",
    "CultureGameModel",
    "FairPriceGameModel",
    "FlashCalcGameModel",
    "ForbiddenWordGameModel",
    "GameSessionModel",
    "GoldenFamilyGameModel",
    "MemoryGameModel",
    "PlayerAccountModel",
    "PlayerSessionModel",
    "RightFlagGameModel",
    "SevenDifferencesGameModel",
    "StopchronoGameModel",
    "VanishingWordGameModel",
]
