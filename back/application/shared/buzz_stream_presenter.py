from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.shared.models.buzz_stream_state import BUZZ_STREAM_FEEDBACK_MS, BuzzStreamState


class BuzzStreamPresenter[StateT: BuzzStreamState](GamePresenter[StateT]):
    def extras(self, state: StateT, teams: list[str]) -> dict[str, Any]:
        return {"feedback_ms": BUZZ_STREAM_FEEDBACK_MS, "winning_score": state.winning_score}
