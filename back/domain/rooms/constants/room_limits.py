"""Équipes et nombre de joueurs d'un salon."""

from __future__ import annotations

TEAM_NAMES = ("Rouges", "Bleus", "Verts", "Jaunes")
MIN_TEAMS, MAX_TEAMS = 2, 4  # au plus autant d'équipes que de noms (vérifié par les tests)
PLAYERS_PER_TEAM = 4
SOLO_MIN_PLAYERS, SOLO_MAX_PLAYERS = 2, 8  # chacun pour soi : l'hôte fixe le nombre maximum de joueurs
