from __future__ import annotations

from typing import Literal

from pydantic import Field

from application.blindtest.commands.fields import DurationMs
from application.shared.commands.input_model import InputModel


class PlaybackSyncCommand(InputModel):
    track_id: str = Field(default="", max_length=120)
    playback_state: Literal["stopped", "playing", "paused"]
    position_ms: DurationMs = 0
    duration_ms: DurationMs = 0
