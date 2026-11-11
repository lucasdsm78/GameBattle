"""Durées de le flux de buzz commun, en millisecondes (ou en secondes quand le nom l'indique)."""

from __future__ import annotations

BUZZ_STREAM_FEEDBACK_MS = 1_500

# Un buzz reçu juste après l'apparition d'un élément est un réflexe sur le précédent : on l'ignore.
BUZZ_STREAM_LOCK_MS = 250
