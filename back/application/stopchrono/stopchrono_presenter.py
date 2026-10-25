from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.stopchrono.models.stopchrono_state import StopChronoState


class StopChronoPresenter(GamePresenter[StopChronoState]):
    def extras(self, state: StopChronoState, teams: list[str]) -> dict[str, Any]:
        return {
            "target_seconds": state.target_ms // 1000,
            "current_team": teams[state.current_team_index] if 0 <= state.current_team_index < len(teams) else None,
            "deltas_ms": {team: abs(elapsed - state.target_ms) for team, elapsed in state.results.items()},
        }
