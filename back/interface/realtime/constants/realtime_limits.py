"""Bornes du temps réel : tailles de messages, files d'envoi, connexions."""

from __future__ import annotations

ROOM_MESSAGE_MAX_CHARS = 256  # le client n'envoie que « pong » et « resync »
MAX_PENDING_REPLIES = 32
MAX_PENDING_EVENTS = 200
ROOM_MAX_PENDING_MESSAGES = 64  # au-delà, le client est trop en retard : on le coupe, il se resynchronisera
CONTROL_MESSAGE_MAX_CHARS = 64 * 1024
MAX_CONNECTIONS_PER_PLAYER = 3  # onglets ou appareils ouverts sur le même salon
