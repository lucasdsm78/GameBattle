from __future__ import annotations

from typing import Literal

from application.blindtest.commands.fields import DurationMs
from application.shared.commands.input_model import InputModel


class PlaybackControlCommand(InputModel):
    action: Literal["play", "pause", "resume", "stop", "seek"]
    position_ms: DurationMs | None = None
