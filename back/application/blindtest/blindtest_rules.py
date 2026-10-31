from __future__ import annotations

from application.shared.game_rules import GameRules

# Écran des règles affiché avant chaque manche de « Blindtest ».
BLINDTEST_RULES = GameRules(
    (
        "Un extrait musical se lance : buzzez dès que vous reconnaissez le titre.",
        "Bonne réponse validée par le présentateur : +1 point.",
        "Mauvaise réponse : l’extrait repart et les autres équipes peuvent buzzer.",
    ),
    "On entend « Bohemian Rhapsody » → buzz → « Queen ! » → +1",
)
