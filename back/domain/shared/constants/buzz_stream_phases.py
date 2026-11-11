"""Phases de le flux de buzz commun : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

BUZZ_STREAM_PHASES = frozenset({"idle", "running", "feedback", "paused", "finished"})
TIMED_PHASES = frozenset({"running", "feedback"})
