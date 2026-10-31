from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.scoring import TIE_LABEL, zero_scores
from domain.stopchrono.events import ChronoRoundStarted, ChronoStarted, ChronoStopped
from exceptions import InvalidGameConfigError

STOPCHRONO_MAX_TARGET_MS = 25000
STOPCHRONO_PHASES = frozenset({"idle", "running", "revealed", "finished"})
# Trois tours, des cibles de plus en plus longues : chaque tour tire la sienne dans sa tranche (en secondes).
STOPCHRONO_TARGET_RANGES_S = ((7, 12), (13, 18), (19, 25))
STOPCHRONO_ROUNDS = len(STOPCHRONO_TARGET_RANGES_S)


def draw_target_ms(round_number: int) -> int:
    low, high = STOPCHRONO_TARGET_RANGES_S[round_number - 1]
    return random.randint(low, high) * 1000


@dataclass(slots=True)
class StopChronoState(GameState):
    """Trois tours, une cible par tour : les écarts s'additionnent, la plus petite erreur totale gagne.

    À chaque tour, l'équipe qui commence change : personne ne joue toujours en dernier.
    """

    game_key: ClassVar[str] = "stopchrono"
    label: ClassVar[str] = "Stop Chrono"

    target_ms: int = 0
    phase: str = "idle"
    current_team_index: int = 0
    started_at_ms: int = 0
    results: dict[str, int] = field(default_factory=dict)  # temps du tour en cours
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None
    round_number: int = 1
    past_targets_ms: list[int] = field(default_factory=list)
    past_results: list[dict[str, int]] = field(default_factory=list)

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> StopChronoState:
        return cls(target_ms=draw_target_ms(1), scores=zero_scores(teams))

    def total_errors_ms(self, teams: list[str]) -> dict[str, int]:
        """Somme des écarts à la cible sur les tours joués, tour en cours compris."""
        rounds = [*zip(self.past_targets_ms, self.past_results), (self.target_ms, self.results)]
        return {
            team: sum(abs(results[team] - target) for target, results in rounds if team in results) for team in teams
        }

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
        if (
            not 1 <= self.round_number <= STOPCHRONO_ROUNDS
            or len(self.past_targets_ms) != self.round_number - 1
            or len(self.past_results) != self.round_number - 1
            or any(not 0 < target <= STOPCHRONO_MAX_TARGET_MS for target in self.past_targets_ms)
            or any(set(results) != allowed_teams or min(results.values()) < 0 for results in self.past_results)
        ):
            raise InvalidGameConfigError("Les tours du stop chrono sont invalides.")

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
        if len(self.results) < len(teams):
            return replace(self, phase="idle", current_team_index=(self.current_team_index + 1) % len(teams), started_at_ms=0)
        if self.round_number < STOPCHRONO_ROUNDS:
            next_round = self.round_number + 1
            return replace(
                self,
                phase="idle",
                round_number=next_round,
                past_targets_ms=[*self.past_targets_ms, self.target_ms],
                past_results=[*self.past_results, dict(self.results)],
                target_ms=draw_target_ms(next_round),
                results={},
                # Rotation : le tour suivant commence par l'équipe suivante.
                current_team_index=(next_round - 1) % len(teams),
                started_at_ms=0,
            )
        # Tous les tours sont joués : la plus petite erreur totale remporte la manche (+1).
        errors = self.total_errors_ms(teams)
        best = min(errors.values())
        closest = [team for team in teams if errors[team] == best]
        scores = {team: int(team in closest) for team in teams}
        winner = closest[0] if len(closest) == 1 else TIE_LABEL
        return replace(self, phase="finished", scores=scores, winner_team=winner, started_at_ms=0)

    def events_since(self, previous: StopChronoState, teams: list[str]) -> list[DomainEvent]:
        team = teams[previous.current_team_index] if previous.current_team_index < len(teams) else None
        if team is None:
            return []
        if self.round_number > previous.round_number:
            return [ChronoRoundStarted(self.round_number, self.target_ms // 1000, first_team=teams[self.current_team_index])]
        if previous.phase == "idle" and self.phase == "running":
            return [ChronoStarted(team)]
        if previous.phase == "running" and self.phase == "revealed":
            elapsed_ms = self.results[team]
            return [ChronoStopped(team, elapsed_ms=elapsed_ms, delta_ms=abs(elapsed_ms - self.target_ms))]
        return []
