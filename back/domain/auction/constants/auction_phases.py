"""Phases de L'Enchère : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

AUCTION_PHASES = frozenset({"idle", "bidding", "ready", "running", "resolved", "finished"})
