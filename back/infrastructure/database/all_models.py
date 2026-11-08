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
from infrastructure.database.models.game_config_model import GameConfigStateModel

__all__ = ["AuthAttemptModel", "GameConfigStateModel", "PlayerAccountModel", "PlayerSessionModel"]
