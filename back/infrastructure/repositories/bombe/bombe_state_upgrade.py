from __future__ import annotations

from typing import Any


def upgrade_bombe_state(bombe: dict[str, Any], teams: list[str]) -> dict[str, Any]:
    """Les anciennes parties en cours n'enregistraient ni pénalités ni équipes en lice."""
    phase = bombe.get("phase", "idle")
    if phase == "idle":
        return bombe
    upgraded = dict(bombe)
    if not bombe.get("scores"):
        upgraded["scores"] = {team: 0 for team in teams}
    if not bombe.get("eligible_team_indices") and phase in {"awaiting_roll", "rolling", "running"}:
        upgraded["eligible_team_indices"] = list(range(len(teams)))
    return upgraded
