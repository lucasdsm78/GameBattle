from __future__ import annotations

from application.shared.game_rules import GameRules
from domain.culture.models.culture_state import CULTURE_QUESTIONS_PER_ROUND

# Écran des règles affiché avant chaque manche de « Culture générale ».
CULTURE_RULES = GameRules(
    (
        f"{CULTURE_QUESTIONS_PER_ROUND} questions, le niveau est choisi avant chacune.",
        "Buzzez pour répondre : bonne réponse, +1 point.",
        "Égalité à la fin : une question difficile départage les équipes.",
    ),
    "« Quel est le plus long fleuve de France ? » → « La Loire ! » → +1",
)
