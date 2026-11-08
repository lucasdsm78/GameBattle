from __future__ import annotations

from typing import Any

from domain.bombe.models.bombe_state import BombeState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class BombeMapper(GameStateMapper[BombeState]):
    state_type = BombeState
    schema_version = 1

    def repair(self, document: dict[str, Any], teams: list[str]) -> dict[str, Any]:
        """Les anciennes parties en cours n'enregistraient ni pénalités ni équipes en lice."""
        phase = document.get("phase", "idle")
        if phase == "idle":
            return document
        repaired = dict(document)
        if not document.get("scores"):
            repaired["scores"] = {team: 0 for team in teams}
        if not document.get("eligible_team_indices") and phase in {"awaiting_roll", "rolling", "running"}:
            repaired["eligible_team_indices"] = list(range(len(teams)))
        return repaired
