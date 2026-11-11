"""Codes de fermeture WebSocket que l'app joueur interprète (4xxx : ne pas se reconnecter en boucle)."""

from __future__ import annotations

# Codes de fermeture que l'app joueur sait interpréter (4xxx : ne pas se reconnecter en boucle).
CLOSE_UNAUTHENTICATED = 4401
CLOSE_NOT_IN_ROOM = 4404
CLOSE_IDLE = 4408
CLOSE_TOO_CHATTY = 4429
CLOSE_LEFT_ROOM = 4000  # fermeture normale : le joueur n'est plus membre (parti, ou salon fermé)
