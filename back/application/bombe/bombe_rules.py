from __future__ import annotations

from application.shared.game_rules import GameRules

# Écran des règles affiché avant chaque manche de « La Bombe ».
BOMBE_RULES = GameRules(
    (
        "Le dé impose la règle : TIC, le mot commence par le son ; TAC, il finit par le son ; BOUM, au choix.",
        "Dites un mot valide puis buzzez pour passer la bombe. Noms propres et marques refusés.",
        "La bombe explose au hasard : l’équipe qui la tient prend une pénalité.",
    ),
    "TIC + « GRAN » → « Grand-mère ! » → buzz, la bombe passe",
)
