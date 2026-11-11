"""Phases de la soirée : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

ALLOWED_STATUSES = frozenset({"configuring", "ready", "live", "finished"})
OPENING_STAGES = frozenset({"", "teams", "rules"})
