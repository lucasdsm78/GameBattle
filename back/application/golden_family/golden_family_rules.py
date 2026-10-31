from __future__ import annotations

from application.shared.game_rules import GameRules
from domain.golden_family.models.golden_family_state import (
    GOLDEN_FAMILY_MAX_STRIKES,
    GOLDEN_FAMILY_WINNING_SCORE,
)

# Écran des règles affiché avant chaque manche de « Une famille en or ».
GOLDEN_FAMILY_RULES = GameRules(
    (
        "Face-à-face : la première équipe à buzzer répond ; la réponse la plus citée prend la main.",
        f"L’équipe qui a la main enchaîne ; à {GOLDEN_FAMILY_MAX_STRIKES} fautes, les autres peuvent la voler.",
        f"Chaque bonne réponse rapporte ses points. Premier à {GOLDEN_FAMILY_WINNING_SCORE}.",
    ),
    "« Un sport regardé le dimanche » → « Football ! » → 34 points",
)
