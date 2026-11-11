"""Réglages des cas d'usage des salons."""

from __future__ import annotations

MUTATION_ATTEMPTS = 3  # reprises après un conflit d'écriture (deux joueurs qui entrent en même temps)
PUBLIC_LIST_LIMIT = 30
QUICK_JOIN_CANDIDATES = 50  # salons publics examinés par « Rejoindre rapidement »
NO_OPEN_PUBLIC_ROOM = "Aucune partie publique n'attend de joueurs pour l'instant."
PUBLIC_ROOM_GONE = "Cette partie n'est plus disponible."
