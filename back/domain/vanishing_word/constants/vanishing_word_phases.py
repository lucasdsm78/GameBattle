"""Phases de Le mot qui disparaît : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

VANISHING_WORD_PHASES = frozenset({"idle", "memorizing", "vanished", "claimed", "revealed", "finished"})
HIDDEN_PHASES = frozenset({"vanished", "claimed"})
