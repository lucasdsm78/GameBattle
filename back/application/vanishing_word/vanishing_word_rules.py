from __future__ import annotations

from application.shared.game_rules import GameRules, seconds
from domain.vanishing_word.models.vanishing_word_state import (
    VANISHING_WORD_MEMORIZATION_MS,
    VANISHING_WORD_WINNING_SCORE,
)

# Écran des règles affiché avant chaque manche de « Le mot qui disparaît ».
VANISHING_WORD_RULES = GameRules(
    (
        f"8 mots s’affichent {seconds(VANISHING_WORD_MEMORIZATION_MS)} secondes : mémorisez-les.",
        "L’un d’eux disparaît : buzzez si vous savez lequel.",
        f"Bonne réponse : +1. Premier à {VANISHING_WORD_WINNING_SCORE} mots trouvés.",
    ),
    "Lion, Pizza, Avion… « Robot » a disparu ! → +1",
)
