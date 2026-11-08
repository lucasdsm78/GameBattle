from __future__ import annotations

from typing import Any

from domain.memory.models.memory_state import MEMORY_RULES_VERSION


def upgrade_memory_state(memory: dict[str, Any], teams: list[str]) -> dict[str, Any]:
    """Les règles v1 ne sont pas rejouables : on ne conserve qu'un éventuel vainqueur."""
    if memory.get("rules_version") == MEMORY_RULES_VERSION:
        return memory
    winner = memory.get("winner_team")
    if memory.get("phase") == "finished" and winner in teams:
        winner_index = teams.index(winner)
        return {
            "phase": "finished",
            "current_team_index": winner_index,
            "qualified_team_indices": [winner_index],
            "disqualified_teams": [team for team in teams if team != winner],
            "winner_team": winner,
        }
    return {}
