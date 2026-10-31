from __future__ import annotations

from application.shared.game_rules import GameRules, seconds
from domain.forbidden_word.models.forbidden_word_state import (
    FORBIDDEN_WORD_SUDDEN_DEATH_MS,
    FORBIDDEN_WORD_TURN_MS,
)

# Écran des règles affiché avant chaque manche de « Le mot interdit ».
FORBIDDEN_WORD_RULES = GameRules(
    (
        f"Chaque équipe a {seconds(FORBIDDEN_WORD_TURN_MS)} secondes pour faire deviner un maximum de mots.",
        "L’orateur ne doit jamais dire le mot, ni ses mots interdits.",
        f"Le plus de mots trouvés gagne ; égalité : mort subite de {seconds(FORBIDDEN_WORD_SUDDEN_DEATH_MS)} secondes.",
    ),
    "« Plage » sans dire sable, mer ni soleil → « On y bronze l’été ! »",
)
