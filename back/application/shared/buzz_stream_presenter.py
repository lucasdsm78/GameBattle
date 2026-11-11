from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.shared.constants.buzz_stream_limits import BUZZ_STREAM_AUTO_PAUSE_AFTER
from domain.shared.constants.buzz_stream_timing import BUZZ_STREAM_FEEDBACK_MS
from domain.shared.models.buzz_stream_state import BuzzStreamState


class BuzzStreamPresenter[StateT: BuzzStreamState](GamePresenter[StateT]):
    internal_fields = frozenset({"unanswered_streak"})

    def extras(self, state: StateT, teams: list[str]) -> dict[str, Any]:
        return {
            "feedback_ms": BUZZ_STREAM_FEEDBACK_MS,
            "winning_score": state.winning_score,
            "auto_pause_after": BUZZ_STREAM_AUTO_PAUSE_AFTER,
        }
