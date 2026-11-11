"""Phases de Mémoire en chaîne : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

MEMORY_PHASES = frozenset({"idle", "question", "recitation", "finished"})
