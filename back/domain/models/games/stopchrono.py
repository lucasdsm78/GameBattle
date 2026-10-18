from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional

from domain.events.base import DomainEvent
from domain.events.stopchrono import ChronoStarted, ChronoStopped
from domain.models.games.base import GameState
from domain.services.scoring import TIE_LABEL, zero_scores
from exceptions import InvalidGameConfigError

STOPCHRONO_MIN_TARGET_MS = 7000
STOPCHRONO_MAX_TARGET_MS = 25000
STOPCHRONO_PHASES = frozenset({"idle", "running", "revealed", "finished"})


@dataclass(slots=True)
class StopChronoState(GameState):
    game_key: ClassVar[str] = "stopchrono"
    label: ClassVar[str] = "Stop Chrono"

    target_ms: int = 0
    phase: str = "idle"
    current_team_index: int = 0
    started_at_ms: int = 0
    results: dict[str, int] = field(default_factory=dict)
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> StopChronoState:
        target_seconds = random.randint(STOPCHRONO_MIN_TARGET_MS // 1000, STOPCHRONO_MAX_TARGET_MS // 1000)
        return cls(target_ms=target_seconds * 1000, scores=zero_scores(teams))

    def validate(self, teams: list[str]) -> None:
        allowed_teams = set(teams)
        if set(self.scores) - allowed_teams:
            raise InvalidGameConfigError("Les scores du stop chrono contiennent une équipe inconnue.")
        if set(self.results) - allowed_teams:
            raise InvalidGameConfigError("Les résultats du stop chrono contiennent une équipe inconnue.")
        if self.winner_team and self.winner_team not in allowed_teams and self.winner_team != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant du stop chrono est inconnu.")
        if self.phase not in STOPCHRONO_PHASES:
            raise InvalidGameConfigError("La phase du stop chrono est invalide.")
        if not 0 <= self.target_ms <= STOPCHRONO_MAX_TARGET_MS:
            raise InvalidGameConfigError("La cible du stop chrono est invalide.")
        if self.current_team_index < 0:
            raise InvalidGameConfigError("L'index d'équipe du stop chrono est invalide.")
        if any(value < 0 for value in self.results.values()):
            raise InvalidGameConfigError("Un temps de stop chrono est invalide.")

    def payload_extras(self, teams: list[str]) -> dict[str, Any]:
        return {
            "target_seconds": self.target_ms // 1000,
            "current_team": teams[self.current_team_index] if 0 <= self.current_team_index < len(teams) else None,
            "deltas_ms": {team: abs(elapsed - self.target_ms) for team, elapsed in self.results.items()},
        }

    def start(self, now_ms: int) -> StopChronoState:
        if self.phase != "idle":
            raise InvalidGameConfigError("Le chrono ne peut démarrer que lorsqu'une équipe est prête.")
        return replace(self, phase="running", started_at_ms=int(now_ms))

    def stop(self, teams: list[str], now_ms: int) -> StopChronoState:
        if self.phase != "running":
            raise InvalidGameConfigError("Aucun chrono en cours à arrêter.")
        if self.current_team_index >= len(teams):
            raise InvalidGameConfigError("Aucune équipe courante pour arrêter le chrono.")
        elapsed_ms = max(int(now_ms) - self.started_at_ms, 0)
        results = {**self.results, teams[self.current_team_index]: elapsed_ms}
        return replace(self, phase="revealed", results=results, started_at_ms=0)

    def next_team(self, teams: list[str]) -> StopChronoState:
        if self.phase != "revealed":
            raise InvalidGameConfigError("Valide d'abord le temps de l'équipe en cours.")
        next_index = self.current_team_index + 1
        if next_index < len(teams):
            return replace(self, phase="idle", current_team_index=next_index, started_at_ms=0)
        # Toutes les équipes ont joué : la plus proche de la cible remporte la manche (+1).
        deltas = {team: abs(elapsed - self.target_ms) for team, elapsed in self.results.items()}
        best = min(deltas.values())
        closest = [team for team, delta in deltas.items() if delta == best]
        scores = {team: int(team in closest) for team in teams}
        winner = closest[0] if len(closest) == 1 else TIE_LABEL
        return replace(self, phase="finished", scores=scores, winner_team=winner, started_at_ms=0)

    def events_since(self, previous: StopChronoState, teams: list[str]) -> list[DomainEvent]:
        team = teams[previous.current_team_index] if previous.current_team_index < len(teams) else None
        if team is None:
            return []
        if previous.phase == "idle" and self.phase == "running":
            return [ChronoStarted(team)]
        if previous.phase == "running" and self.phase == "revealed":
            elapsed_ms = self.results[team]
            return [ChronoStopped(team, elapsed_ms=elapsed_ms, delta_ms=abs(elapsed_ms - self.target_ms))]
        return []
