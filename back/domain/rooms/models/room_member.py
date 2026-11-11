from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoomMember:
    """Un joueur dans un salon. En solo, son « équipe » est son pseudo : chacun joue pour soi."""

    account_id: str
    pseudo: str
    team: str
    joined_at_ms: int
