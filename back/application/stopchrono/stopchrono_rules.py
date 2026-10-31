from __future__ import annotations

from application.shared.game_rules import GameRules
from domain.stopchrono.models.stopchrono_state import STOPCHRONO_ROUNDS

# Écran des règles affiché avant chaque manche de « Stop Chrono ».
STOPCHRONO_RULES = GameRules(
    (
        f"{STOPCHRONO_ROUNDS} tours, une nouvelle cible à chaque tour.",
        "Démarrez puis arrêtez le chrono… sans le voir défiler.",
        "Les écarts s’additionnent : la plus petite erreur totale gagne.",
    ),
    "Cible 14 s, vous arrêtez à 13,6 s → 0,4 s d’erreur",
)
