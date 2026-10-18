from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional

from domain.models.games.base import GameState
from domain.services.catalogs.seven_differences import pick_seven_differences_puzzle
from domain.services.scoring import TIE_LABEL, pick_round_winner, zero_scores
from domain.vo.seven_difference import SevenDifference
from exceptions import InvalidGameConfigError

SEVEN_DIFFERENCES_PHASES = frozenset({"idle", "memorizing", "open", "claimed", "finished"})
SEVEN_DIFFERENCES_MEMORIZATION_MS = 25_000
DIFFERENCE_COUNT = 7


@dataclass(slots=True)
class SevenDifferencesState(GameState):
    game_key: ClassVar[str] = "seven_differences"
    label: ClassVar[str] = "Les 7 différences"

    phase: str = "idle"
    puzzle_id: str = ""
    title: str = ""
    original_image_url: str = ""
    modified_image_url: str = ""
    differences: list[SevenDifference] = field(default_factory=list)
    found_difference_ids: list[str] = field(default_factory=list)
    reveal_at_ms: int = 0
    current_buzzer_team: Optional[str] = None
    blocked_team: Optional[str] = None
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> SevenDifferencesState:
        return cls(scores=zero_scores(teams))

    def validate(self, teams: list[str]) -> None:
        allowed_teams = set(teams)
        difference_ids = [difference.id for difference in self.differences]
        found_ids = set(self.found_difference_ids)
        if self.phase not in SEVEN_DIFFERENCES_PHASES:
            raise InvalidGameConfigError("La phase des 7 différences est invalide.")
        if self.phase == "idle":
            if any((
                self.puzzle_id,
                self.title,
                self.original_image_url,
                self.modified_image_url,
                self.differences,
                self.found_difference_ids,
                self.reveal_at_ms,
                self.current_buzzer_team,
                self.blocked_team,
                self.winner_team,
            )):
                raise InvalidGameConfigError("L’état initial des 7 différences est invalide.")
            if set(self.scores) - allowed_teams or any(score != 0 for score in self.scores.values()):
                raise InvalidGameConfigError("Les scores initiaux des 7 différences sont invalides.")
            return
        if len(difference_ids) != DIFFERENCE_COUNT or len(set(difference_ids)) != DIFFERENCE_COUNT:
            raise InvalidGameConfigError("Une image doit contenir exactement 7 différences uniques.")
        if not all((self.puzzle_id, self.title, self.original_image_url, self.modified_image_url)):
            raise InvalidGameConfigError("Le puzzle des 7 différences est incomplet.")
        if found_ids - set(difference_ids) or len(found_ids) != len(self.found_difference_ids):
            raise InvalidGameConfigError("Les différences trouvées sont invalides.")
        if any(not difference.id or not difference.label.strip() for difference in self.differences):
            raise InvalidGameConfigError("Les descriptions des 7 différences sont invalides.")
        if self.current_buzzer_team and self.current_buzzer_team not in allowed_teams:
            raise InvalidGameConfigError("L’équipe qui a la main est inconnue.")
        if self.blocked_team and self.blocked_team not in allowed_teams:
            raise InvalidGameConfigError("L’équipe temporairement bloquée est inconnue.")
        if set(self.scores) != allowed_teams or any(not isinstance(score, int) or score < 0 for score in self.scores.values()):
            raise InvalidGameConfigError("Les scores des 7 différences sont invalides.")
        if sum(self.scores.values()) != len(found_ids):
            raise InvalidGameConfigError("Le total des scores des 7 différences est incohérent.")
        if self.winner_team and self.winner_team not in allowed_teams and self.winner_team != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant des 7 différences est inconnu.")
        if self.reveal_at_ms <= 0:
            raise InvalidGameConfigError("L’échéance de mémorisation est invalide.")
        if self.phase == "memorizing" and (self.current_buzzer_team or self.blocked_team or found_ids or self.winner_team):
            raise InvalidGameConfigError("La phase de mémorisation des 7 différences est invalide.")
        if self.phase == "open" and (self.current_buzzer_team or self.winner_team or len(found_ids) == DIFFERENCE_COUNT):
            raise InvalidGameConfigError("La phase ouverte des 7 différences est invalide.")
        if self.phase == "claimed" and (
            not self.current_buzzer_team or self.blocked_team or self.winner_team or len(found_ids) == DIFFERENCE_COUNT
        ):
            raise InvalidGameConfigError("La prise de main des 7 différences est invalide.")
        if self.phase == "finished" and (
            len(found_ids) != DIFFERENCE_COUNT
            or self.current_buzzer_team
            or self.blocked_team
            or self.winner_team != pick_round_winner(teams, self.scores)
        ):
            raise InvalidGameConfigError("La fin de manche des 7 différences est invalide.")

    def payload_extras(self, teams: list[str]) -> dict[str, Any]:
        return {"differences_remaining": DIFFERENCE_COUNT - len(self.found_difference_ids)}

    @staticmethod
    def display_view(payload: dict[str, Any]) -> dict[str, Any]:
        view = {**payload, "differences": []}
        if payload.get("phase") in {"idle", "memorizing"}:
            view["modified_image_url"] = ""
        return view

    def start(self, teams: list[str], now_ms: int) -> SevenDifferencesState:
        if self.phase != "idle":
            raise InvalidGameConfigError("La manche des 7 différences a déjà commencé.")
        puzzle = pick_seven_differences_puzzle()
        return SevenDifferencesState(
            phase="memorizing",
            puzzle_id=puzzle.id,
            title=puzzle.title,
            original_image_url=puzzle.original_image_url,
            modified_image_url=puzzle.modified_image_url,
            differences=[SevenDifference(id=id_, label=label) for id_, label in puzzle.differences],
            reveal_at_ms=now_ms + SEVEN_DIFFERENCES_MEMORIZATION_MS,
            scores=zero_scores(teams),
        )

    def open(self, now_ms: int) -> SevenDifferencesState:
        if self.phase in {"open", "claimed", "finished"}:
            return self
        if self.phase != "memorizing":
            raise InvalidGameConfigError("La phase de mémorisation n’est pas active.")
        if now_ms < self.reveal_at_ms:
            raise InvalidGameConfigError("Les 25 secondes de mémorisation ne sont pas terminées.")
        return replace(self, phase="open")

    def register_buzzer(self, teams: list[str], team: str, now_ms: int) -> SevenDifferencesState:
        if team not in teams:
            raise InvalidGameConfigError("L’équipe qui buzze est inconnue.")
        state = self
        if state.phase == "memorizing":
            if now_ms < state.reveal_at_ms:
                raise InvalidGameConfigError("Les buzzers s’ouvrent après les 25 secondes de mémorisation.")
            state = replace(state, phase="open")
        if state.phase != "open":
            raise InvalidGameConfigError("Les buzzers ne sont pas disponibles actuellement.")
        if team == state.blocked_team:
            raise InvalidGameConfigError("Cette équipe doit attendre qu’une autre équipe prenne la main.")
        return replace(state, phase="claimed", current_buzzer_team=team, blocked_team=None)

    def find(self, teams: list[str], difference_id: str) -> SevenDifferencesState:
        if self.phase != "claimed" or not self.current_buzzer_team:
            raise InvalidGameConfigError("Aucune équipe n’a la main.")
        available_ids = {difference.id for difference in self.differences} - set(self.found_difference_ids)
        if difference_id not in available_ids:
            raise InvalidGameConfigError("Cette différence est inconnue ou déjà trouvée.")
        found_ids = [*self.found_difference_ids, difference_id]
        team = self.current_buzzer_team
        scores = {**self.scores, team: self.scores.get(team, 0) + 1}
        if len(found_ids) < DIFFERENCE_COUNT:
            return replace(self, found_difference_ids=found_ids, scores=scores)
        return replace(
            self,
            phase="finished",
            found_difference_ids=found_ids,
            current_buzzer_team=None,
            blocked_team=None,
            scores=scores,
            winner_team=pick_round_winner(teams, scores),
        )

    def reject(self) -> SevenDifferencesState:
        if self.phase != "claimed" or not self.current_buzzer_team:
            raise InvalidGameConfigError("Aucune réponse ne peut être refusée actuellement.")
        return replace(self, phase="open", blocked_team=self.current_buzzer_team, current_buzzer_team=None)
