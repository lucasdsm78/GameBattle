from __future__ import annotations

from dataclasses import dataclass

from application.shared.attempt_limit import AttemptLimit

_MINUTE_MS = 60_000


@dataclass(frozen=True, slots=True)
class RoomLimits:
    """Un code d'invitation est un secret : on ne le devine pas par essais successifs, et on ne crée pas de salons en rafale."""

    invitation_lookups_per_ip: AttemptLimit = AttemptLimit("room_code", limit=30, window_ms=15 * _MINUTE_MS)
    rooms_created_per_player: AttemptLimit = AttemptLimit("room_create", limit=10, window_ms=60 * _MINUTE_MS)
    inactive_after_ms: int = 6 * 60 * _MINUTE_MS  # salon sans activité depuis 6 h : fermé par le ménage
