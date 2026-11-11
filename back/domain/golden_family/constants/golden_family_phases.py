"""Phases de Une famille en or : ensembles fermés de valeurs, enregistrés tels quels dans l'état de la partie."""

from __future__ import annotations

GOLDEN_FAMILY_PHASES = frozenset({"idle", "faceoff", "duel", "control", "steal", "revealed", "finished"})

# duel : chaque équipe donne une réponse pour prendre la main ; control : l'équipe qui a la main enchaîne ;
# steal : après 3 fautes, les autres équipes tentent une réponse chacune.
ANSWERING_PHASES = frozenset({"duel", "control", "steal"})
