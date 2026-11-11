from __future__ import annotations

from typing import Any

from domain.memory.constants.memory_limits import MEMORY_RULES_VERSION
from domain.memory.models.memory_state import MemoryState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class MemoryMapper(GameStateMapper[MemoryState]):
    state_type = MemoryState
    schema_version = 1

    def repair(self, document: dict[str, Any], teams: list[str]) -> dict[str, Any]:
        """Les règles v1 ne sont pas rejouables : on ne conserve qu'un éventuel vainqueur."""
        if document.get("rules_version") == MEMORY_RULES_VERSION:
            return document
        winner = document.get("winner_team")
        if document.get("phase") == "finished" and winner in teams:
            winner_index = teams.index(winner)
            return {
                "phase": "finished",
                "current_team_index": winner_index,
                "qualified_team_indices": [winner_index],
                "disqualified_teams": [team for team in teams if team != winner],
                "winner_team": winner,
            }
        return {}
