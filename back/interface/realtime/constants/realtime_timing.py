"""Délais du temps réel, en secondes."""

from __future__ import annotations

HEARTBEAT_SECONDS = 20.0
IDLE_TIMEOUT_SECONDS = 50.0  # plus de deux pings sans réponse : connexion morte
SESSION_RECHECK_SECONDS = 60.0  # une déconnexion ailleurs (ou une session expirée) coupe aussi le temps réel
SEND_TIMEOUT_SECONDS = 5.0
