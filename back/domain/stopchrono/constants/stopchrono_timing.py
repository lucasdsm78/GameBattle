"""Durées de Stop Chrono, en millisecondes (ou en secondes quand le nom l'indique)."""

from __future__ import annotations

STOPCHRONO_MAX_TARGET_MS = 25000

# Trois tours, des cibles de plus en plus longues : chaque tour tire la sienne dans sa tranche (en secondes).
STOPCHRONO_TARGET_RANGES_S = ((7, 12), (13, 18), (19, 25))
