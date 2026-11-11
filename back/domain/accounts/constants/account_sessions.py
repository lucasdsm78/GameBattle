"""Durée des sessions et seuil de prolongation (session glissante)."""

from __future__ import annotations

SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000

# Un joueur actif n'est jamais déconnecté : passé la moitié de sa durée, la session repart pour 30 jours.
# Au plus une écriture tous les 15 jours par session, au lieu d'une à chaque visite.
SESSION_RENEW_AFTER_MS = SESSION_TTL_MS // 2
