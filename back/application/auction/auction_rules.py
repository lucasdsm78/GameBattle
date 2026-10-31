from __future__ import annotations

from application.shared.game_rules import GameRules, seconds
from domain.auction.models.auction_state import (
    AUCTION_DURATION_MS,
    AUCTION_FAILURE_POINTS,
    AUCTION_WINNING_SCORE,
)

# Écran des règles affiché avant chaque manche de « L’Enchère ».
AUCTION_RULES = GameRules(
    (
        "Un thème est annoncé : buzzez puis annoncez combien de réponses vous pouvez donner.",
        f"La plus grosse enchère joue : {seconds(AUCTION_DURATION_MS)} secondes pour tenir son annonce.",
        f"Réussi : autant de points que l’annonce. Raté : +{AUCTION_FAILURE_POINTS} pour les autres. Premier à {AUCTION_WINNING_SCORE}.",
    ),
    "« Pays d’Europe » → « On en donne 6 ! » → 6 réponses → +6",
)
