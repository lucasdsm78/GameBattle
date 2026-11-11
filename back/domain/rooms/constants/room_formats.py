"""Comment on joue dans un salon."""

from __future__ import annotations

from enum import StrEnum


class RoomFormat(StrEnum):
    SOLO = "solo"  # chacun pour soi : chaque joueur joue pour sa peau
    TEAMS = "teams"  # en équipes
