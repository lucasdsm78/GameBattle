"""Phases de Le juste prix : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

FAIR_PRICE_PHASES = frozenset({"idle", "ready", "running", "finished"})
