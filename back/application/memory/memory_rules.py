from __future__ import annotations

from application.shared.game_rules import GameRules
from domain.memory.models.memory_state import MEMORY_CHAIN_LENGTH

# Écran des règles affiché avant chaque manche de « Mémoire en chaîne ».
MEMORY_RULES = GameRules(
    (
        f"Une équipe reçoit {MEMORY_CHAIN_LENGTH} questions d’affilée et retient chaque réponse.",
        f"Elle récite ensuite les {MEMORY_CHAIN_LENGTH} réponses, dans l’ordre exact.",
        "Une erreur et l’équipe est éliminée : la dernière en jeu gagne.",
    ),
    "Réponses : Paris, 7, Mozart… → à réciter dans cet ordre",
)
