from __future__ import annotations

from application.shared.game_rules import GameRules, seconds
from domain.fair_price.constants.fair_price_timing import FAIR_PRICE_TURN_MS

# Écran des règles affiché avant chaque manche de « Le juste prix ».
FAIR_PRICE_RULES = GameRules(
    (
        "Chaque équipe, à son tour, reçoit un objet différent, de la même gamme de prix.",
        "Annoncez des prix : le présentateur répond « c’est plus » ou « c’est moins ».",
        f"L’équipe qui trouve le juste prix le plus vite gagne ({seconds(FAIR_PRICE_TURN_MS)} s maximum).",
    ),
    "« 300 € ! » → c’est plus · « 500 € ! » → c’est moins · « 499 € ! » → trouvé",
)
