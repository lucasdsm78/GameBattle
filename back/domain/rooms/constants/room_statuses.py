"""Statuts d'un salon."""

from __future__ import annotations

from enum import StrEnum


class RoomStatus(StrEnum):
    LOBBY = "lobby"  # salle d'attente : on entre, on sort, on change d'équipe
    CLOSED = "closed"  # dernier départ ou inactivité : le salon disparaît, son lien aussi
