from __future__ import annotations

from application.shared.game_rules import GameRules
from domain.shared.models.buzz_stream_state import BUZZ_STREAM_WINNING_SCORE

# Écran des règles affiché avant chaque manche de « Calcul flash ».
FLASH_CALC_RULES = GameRules(
    (
        "Des calculs défilent, de plus en plus vite.",
        "Buzzez seulement si le résultat est juste : +1 ; faux, −1 (jamais sous 0).",
        f"Premier à {BUZZ_STREAM_WINNING_SCORE} points.",
    ),
    "7 × 8 = 54 → on ne buzze pas · 7 × 8 = 56 → on buzze !",
)
