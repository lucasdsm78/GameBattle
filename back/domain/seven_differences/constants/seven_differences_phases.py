"""Phases de Les 7 différences : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

SEVEN_DIFFERENCES_PHASES = frozenset({"idle", "memorizing", "open", "claimed", "finished"})
