"""Phases de La Bombe : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

BOMBE_PHASES = frozenset({"idle", "awaiting_roll", "rolling", "running", "exploded"})
