from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional

from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.auction_catalog import pick_auction_theme
from domain.game_config.model.shared import TIE_LABEL, GameState, zero_scores

AUCTION_PHASES = frozenset({"idle", "bidding", "ready", "running", "resolved", "finished"})
AUCTION_DURATION_MS = 30_000
AUCTION_WINNING_SCORE = 20
AUCTION_MAX_TARGET_COUNT = 100
AUCTION_FAILURE_POINTS = 2


@dataclass(slots=True)
class AuctionState(GameState):
    game_key: ClassVar[str] = "auction"
    label: ClassVar[str] = "L’Enchère"
    private_fields: ClassVar[frozenset[str]] = frozenset({"asked_theme_ids"})

    phase: str = "idle"
    theme_id: str = ""
    prompt: str = ""
    answers: list[str] = field(default_factory=list)
    bidding_teams: list[str] = field(default_factory=list)
    active_team: Optional[str] = None
    target_count: int = 0
    correct_count: int = 0
    started_at_ms: int = 0
    deadline_at_ms: int = 0
    scores: dict[str, int] = field(default_factory=dict)
    attempt_succeeded: Optional[bool] = None
    points_awarded: dict[str, int] = field(default_factory=dict)
    asked_theme_ids: list[str] = field(default_factory=list)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> AuctionState:
        return cls(scores=zero_scores(teams))

    def validate(self, teams: list[str]) -> None:
        allowed = set(teams)
        if self.phase not in AUCTION_PHASES:
            raise InvalidGameConfigError("La phase de L’Enchère est invalide.")
        if self.phase == "idle" and not self.scores:
            return
        if set(self.scores) != allowed or any(not isinstance(score, int) or score < 0 for score in self.scores.values()):
            raise InvalidGameConfigError("Les scores de L’Enchère sont invalides.")
        if len(set(self.bidding_teams)) != len(self.bidding_teams) or set(self.bidding_teams) - allowed:
            raise InvalidGameConfigError("Les équipes ayant buzzé pour L’Enchère sont invalides.")
        if self.active_team and self.active_team not in allowed:
            raise InvalidGameConfigError("L’équipe active de L’Enchère est inconnue.")
        if self.winner_team and self.winner_team not in allowed and self.winner_team != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant de L’Enchère est inconnu.")
        if self.phase != "idle" and (not self.theme_id or not self.prompt or not self.answers):
            raise InvalidGameConfigError("Le thème de L’Enchère est incomplet.")
        if self.correct_count < 0 or self.correct_count > self.target_count:
            raise InvalidGameConfigError("Le compteur de L’Enchère est invalide.")
        if self.phase in {"ready", "running", "resolved", "finished"} and (
            not self.active_team or not 1 <= self.target_count <= AUCTION_MAX_TARGET_COUNT
        ):
            raise InvalidGameConfigError("L’enchère sélectionnée est invalide.")
        if self.phase == "running" and (self.started_at_ms <= 0 or self.deadline_at_ms - self.started_at_ms != AUCTION_DURATION_MS):
            raise InvalidGameConfigError("Le chrono de L’Enchère est invalide.")
        if self.phase in {"resolved", "finished"} and self.attempt_succeeded is None:
            raise InvalidGameConfigError("Le résultat de L’Enchère est manquant.")

    @staticmethod
    def display_view(payload: dict[str, Any]) -> dict[str, Any]:
        return {**payload, "answers": []}

    def _draw_theme(self, scores: dict[str, int]) -> AuctionState:
        theme = pick_auction_theme(self.asked_theme_ids)
        return AuctionState(
            phase="bidding",
            theme_id=theme.id,
            prompt=theme.prompt,
            answers=list(theme.answers),
            scores=scores,
            asked_theme_ids=[*self.asked_theme_ids, theme.id],
        )

    def start(self, teams: list[str]) -> AuctionState:
        if self.phase != "idle":
            raise InvalidGameConfigError("L’Enchère a déjà commencé.")
        return self._draw_theme(dict(self.scores) or zero_scores(teams))

    def next_theme(self) -> AuctionState:
        if self.phase != "resolved":
            raise InvalidGameConfigError("Le thème suivant est disponible après la résolution.")
        return self._draw_theme(dict(self.scores))

    def register_buzzer(self, teams: list[str], team: str) -> AuctionState:
        if team not in teams:
            raise InvalidGameConfigError("L’équipe qui buzze est inconnue.")
        if self.phase == "bidding":
            return self if team in self.bidding_teams else replace(self, bidding_teams=[*self.bidding_teams, team])
        if self.phase == "running":
            if team != self.active_team:
                raise InvalidGameConfigError("Seule l’équipe en jeu peut terminer sa tentative.")
            return self._resolve(teams)
        raise InvalidGameConfigError("Les buzzers de L’Enchère ne sont pas disponibles actuellement.")

    def select_bid(self, teams: list[str], team: str, target_count: int) -> AuctionState:
        if self.phase != "bidding":
            raise InvalidGameConfigError("L’enchère ne peut être attribuée que pendant les mises.")
        if team not in teams:
            raise InvalidGameConfigError("L’équipe sélectionnée est inconnue.")
        if not 1 <= target_count <= AUCTION_MAX_TARGET_COUNT:
            raise InvalidGameConfigError(f"Le nombre de réponses doit être compris entre 1 et {AUCTION_MAX_TARGET_COUNT}.")
        return replace(
            self, phase="ready", active_team=team, target_count=target_count, correct_count=0, attempt_succeeded=None, points_awarded={}
        )

    def launch(self, now_ms: int) -> AuctionState:
        if self.phase != "ready":
            raise InvalidGameConfigError("Sélectionnez d’abord l’équipe et son enchère.")
        return replace(self, phase="running", started_at_ms=now_ms, deadline_at_ms=now_ms + AUCTION_DURATION_MS)

    def change_count(self, teams: list[str], delta: int, now_ms: int) -> AuctionState:
        if self.phase != "running":
            raise InvalidGameConfigError("Le compteur est disponible uniquement pendant le chrono.")
        if now_ms >= self.deadline_at_ms:
            return self._resolve(teams)
        if delta not in {-1, 1}:
            raise InvalidGameConfigError("La correction du compteur est invalide.")
        count = min(self.target_count, max(0, self.correct_count + delta))
        return self if count == self.correct_count else replace(self, correct_count=count)

    def expire(self, teams: list[str], now_ms: int) -> AuctionState:
        if self.phase in {"resolved", "finished"}:
            return self
        if self.phase != "running":
            raise InvalidGameConfigError("Aucune tentative de L’Enchère n’est en cours.")
        if now_ms < self.deadline_at_ms:
            raise InvalidGameConfigError("Les 30 secondes ne sont pas encore écoulées.")
        return self._resolve(teams)

    def expire_due(self, teams: list[str], now_ms: int) -> AuctionState:
        return self._resolve(teams) if self.phase == "running" and now_ms >= self.deadline_at_ms else self

    def _resolve(self, teams: list[str]) -> AuctionState:
        succeeded = self.correct_count >= self.target_count
        if succeeded and self.active_team:
            points = {team: self.target_count if team == self.active_team else 0 for team in teams}
        else:
            points = {team: 0 if team == self.active_team else AUCTION_FAILURE_POINTS for team in teams}
        scores = {team: self.scores.get(team, 0) + points[team] for team in teams}
        at_target = [team for team in teams if scores[team] >= AUCTION_WINNING_SCORE]
        winner: Optional[str] = None
        if at_target:
            best = max(scores[team] for team in at_target)
            leaders = [team for team in at_target if scores[team] == best]
            winner = leaders[0] if len(leaders) == 1 else TIE_LABEL
        return replace(
            self,
            phase="finished" if winner else "resolved",
            scores=scores,
            attempt_succeeded=succeeded,
            points_awarded=points,
            winner_team=winner,
        )
