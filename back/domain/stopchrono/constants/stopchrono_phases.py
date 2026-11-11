"""Phases de Stop Chrono : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

STOPCHRONO_PHASES = frozenset({"idle", "running", "revealed", "finished"})
