"""Phases de Le mot interdit : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

FORBIDDEN_WORD_PHASES = frozenset({"idle", "ready", "running", "finished"})
