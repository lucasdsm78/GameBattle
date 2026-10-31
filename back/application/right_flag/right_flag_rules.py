from __future__ import annotations

from application.shared.game_rules import GameRules
from domain.shared.models.buzz_stream_state import BUZZ_STREAM_WINNING_SCORE

# Écran des règles affiché avant chaque manche de « Le bon drapeau ».
RIGHT_FLAG_RULES = GameRules(
    (
        "Un pays s’affiche, puis des drapeaux défilent.",
        "Buzzez sur le bon drapeau : +1 ; mauvais drapeau, −1 (jamais sous 0).",
        f"Premier à {BUZZ_STREAM_WINNING_SCORE} points.",
    ),
    "« Brésil » → buzz sur le drapeau vert et jaune → +1",
)
