from __future__ import annotations

from application.shared.game_rules import GameRules, seconds
from domain.seven_differences.models.seven_differences_state import (
    DIFFERENCE_COUNT,
    SEVEN_DIFFERENCES_MEMORIZATION_MS,
)

# Écran des règles affiché avant chaque manche de « Les 7 différences ».
SEVEN_DIFFERENCES_RULES = GameRules(
    (
        f"L’image originale s’affiche {seconds(SEVEN_DIFFERENCES_MEMORIZATION_MS)} secondes : observez bien.",
        "Elle est remplacée par une copie modifiée : buzzez et montrez une différence.",
        f"Chaque différence trouvée rapporte 1 point ; les {DIFFERENCE_COUNT} trouvées, le meilleur score gagne.",
    ),
    "« Le chat a disparu de la fenêtre ! » → +1",
)
