"""Scores, quantités et bornes de le flux de buzz commun."""

from __future__ import annotations

BUZZ_STREAM_WINNING_SCORE = 5

# Après autant d'éléments d'affilée sans aucun buzz, personne ne joue : le défilement se met en pause seul,
# et le serveur cesse d'écrire et de diffuser.
BUZZ_STREAM_AUTO_PAUSE_AFTER = 15
