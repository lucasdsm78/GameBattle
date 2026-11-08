"""Point d'agrégation des tables, réservé au schéma : Alembic et `Database.create_schema` l'importent avant de
lire `Base.metadata`. Ce n'est pas un point d'accès métier : le code d'un module importe ses propres modèles,
jamais ce fichier (règle vérifiée par `tests/test_architecture.py`).
"""

from infrastructure.database.models.accounts.auth_attempt_model import AuthAttemptModel
from infrastructure.database.models.accounts.player_account_model import (
    PlayerAccountModel,
)
from infrastructure.database.models.accounts.player_session_model import (
    PlayerSessionModel,
)
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
from infrastructure.database.models.game_night.game_night_model import GameNightModel
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
from infrastructure.database.models.stopchrono.stopchrono_game_model import (
    StopchronoGameModel,
)
from infrastructure.database.models.vanishing_word.vanishing_word_game_model import (
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
    "GameNightModel",
    "GoldenFamilyGameModel",
    "MemoryGameModel",
    "PlayerAccountModel",
    "PlayerSessionModel",
    "RightFlagGameModel",
    "SevenDifferencesGameModel",
    "StopchronoGameModel",
    "VanishingWordGameModel",
]
