from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.forbidden_word.events import (
    SuddenDeathStarted,
    TurnEnded,
    TurnStarted,
    WordFound,
    WordSkipped,
)
from domain.forbidden_word.models.forbidden_word_card import (
    ForbiddenWordCard,
    ForbiddenWordTurn,
)
from domain.forbidden_word.services.forbidden_word_catalog import (
    pick_forbidden_word_card,
)
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.scoring import pick_round_winner
from exceptions import InvalidGameConfigError

FORBIDDEN_WORD_PHASES = frozenset({"idle", "ready", "running", "finished"})
FORBIDDEN_WORD_TURN_MS = 60_000
FORBIDDEN_WORD_SUDDEN_DEATH_MS = 20_000


def draw_forbidden_word_card(used_card_ids: list[str]) -> tuple[ForbiddenWordCard, list[str]]:
    picked = pick_forbidden_word_card(used_card_ids)
    if picked is None:
        # Catalogue épuisé : on recommence un cycle complet plutôt que de bloquer la manche.
        used_card_ids = []
        picked = pick_forbidden_word_card(used_card_ids)
    if picked is None:
        raise InvalidGameConfigError("Le catalogue du Mot interdit est vide.")
    card = ForbiddenWordCard(id=picked.id, word=picked.word, forbidden_words=list(picked.forbidden_words))
    return card, [*used_card_ids, card.id]


@dataclass(slots=True)
class ForbiddenWordState(GameState):
    """Chaque équipe joue un tour de 60 s, dans un ordre tiré au sort ; les scores sont dérivés des tours.

    En cas d'égalité en tête, les équipes concernées rejouent 20 s chacune (mort subite), autant de fois
    qu'il le faut pour les départager.
    """

    game_key: ClassVar[str] = "forbidden_word"
    label: ClassVar[str] = "Le mot interdit"

    phase: str = "idle"
    turn_order: list[str] = field(default_factory=list)
    turns: list[ForbiddenWordTurn] = field(default_factory=list)
    current_card: Optional[ForbiddenWordCard] = None
    started_at_ms: int = 0
    deadline_at_ms: int = 0
    used_card_ids: list[str] = field(default_factory=list)
    sudden_death_round: int = 0
    sudden_death_teams: list[str] = field(default_factory=list)  # équipes à égalité, dans l'ordre de passage
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> ForbiddenWordState:
        return cls(phase="ready", turn_order=random.sample(teams, len(teams)))

    @property
    def round_order(self) -> list[str]:
        return self.sudden_death_teams if self.sudden_death_round else self.turn_order

    @property
    def round_turns(self) -> list[ForbiddenWordTurn]:
        return [turn for turn in self.turns if turn.round == self.sudden_death_round]

    @property
    def turn_duration_ms(self) -> int:
        return FORBIDDEN_WORD_SUDDEN_DEATH_MS if self.sudden_death_round else FORBIDDEN_WORD_TURN_MS

    @property
    def current_team(self) -> Optional[str]:
        if self.phase == "ready":
            return self.round_order[len(self.round_turns)]
        if self.phase == "running":
            return self.turns[-1].team
        return None

    def scores(self, teams: list[str]) -> dict[str, int]:
        """Tous les mots trouvés, mort subite comprise : le départage ne peut que creuser l'écart."""
        scores = {team: 0 for team in teams}
        for turn in self.turns:
            scores[turn.team] += len(turn.found_words)
        return scores

    def validate(self, teams: list[str]) -> None:
        if self.phase not in FORBIDDEN_WORD_PHASES:
            raise InvalidGameConfigError("La phase du Mot interdit est invalide.")
        if self.phase == "idle":
            if any((self.turn_order, self.turns, self.current_card, self.started_at_ms, self.deadline_at_ms, self.used_card_ids, self.winner_team)):
                raise InvalidGameConfigError("L’état initial du Mot interdit est invalide.")
            return
        if sorted(self.turn_order) != sorted(teams):
            raise InvalidGameConfigError("L’ordre de passage du Mot interdit est invalide.")
        main_turns = [turn.team for turn in self.turns if turn.round == 0]
        rounds = [turn.round for turn in self.turns]
        if main_turns != self.turn_order[: len(main_turns)] or rounds != sorted(rounds) or rounds[-1:] > [self.sudden_death_round]:
            raise InvalidGameConfigError("Les tours du Mot interdit ne respectent pas l’ordre de passage.")
        if self.sudden_death_round and (
            len(main_turns) != len(teams)
            or len(self.sudden_death_teams) < 2
            or len(set(self.sudden_death_teams)) != len(self.sudden_death_teams)
            or set(self.sudden_death_teams) - set(teams)
            or [turn.team for turn in self.round_turns] != self.sudden_death_teams[: len(self.round_turns)]
        ) or (not self.sudden_death_round and self.sudden_death_teams):
            raise InvalidGameConfigError("La mort subite du Mot interdit est invalide.")
        if len(set(self.used_card_ids)) != len(self.used_card_ids):
            raise InvalidGameConfigError("Un mot du Mot interdit a été tiré plusieurs fois.")
        if self.phase == "ready" and (
            len(self.round_turns) >= len(self.round_order)
            or self.current_card
            or self.started_at_ms
            or self.deadline_at_ms
            or self.winner_team
        ):
            raise InvalidGameConfigError("La préparation du tour du Mot interdit est invalide.")
        if self.phase == "running" and (
            not self.turns
            or self.current_card is None
            or self.current_card.id not in self.used_card_ids
            or self.started_at_ms <= 0
            or self.deadline_at_ms - self.started_at_ms != self.turn_duration_ms
            or self.winner_team
        ):
            raise InvalidGameConfigError("Le tour en cours du Mot interdit est invalide.")
        if self.phase == "finished" and (
            len(self.round_turns) != len(self.round_order)
            or self.current_card
            or self.winner_team != pick_round_winner(teams, self.scores(teams))
        ):
            raise InvalidGameConfigError("La fin de manche du Mot interdit est invalide.")

    def start_turn(self, now_ms: int) -> ForbiddenWordState:
        if self.phase != "ready":
            raise InvalidGameConfigError("Le tour ne peut démarrer que lorsque l’équipe est prête.")
        card, used_card_ids = draw_forbidden_word_card(self.used_card_ids)
        return replace(
            self,
            phase="running",
            turns=[*self.turns, ForbiddenWordTurn(team=self.current_team or "", round=self.sudden_death_round)],
            current_card=card,
            used_card_ids=used_card_ids,
            started_at_ms=now_ms,
            deadline_at_ms=now_ms + self.turn_duration_ms,
        )

    def resolve_card(self, teams: list[str], card_id: str, *, found: bool, now_ms: int) -> ForbiddenWordState:
        """Valide (TROUVÉ) ou passe la carte affichée puis tire la suivante.

        `card_id` rend la commande idempotente : un double appui, ou un appui arrivé après le tirage
        suivant ou la fin du tour, est ignoré au lieu de compter deux fois ou d'afficher une erreur.
        """
        if self.phase != "running" or self.current_card is None or self.current_card.id != card_id:
            return self
        if now_ms >= self.deadline_at_ms:
            return self._end_turn(teams)
        turn = self.turns[-1]
        word = self.current_card.word
        resolved_turn = (
            replace(turn, found_words=[*turn.found_words, word]) if found else replace(turn, skipped_words=[*turn.skipped_words, word])
        )
        card, used_card_ids = draw_forbidden_word_card(self.used_card_ids)
        return replace(self, turns=[*self.turns[:-1], resolved_turn], current_card=card, used_card_ids=used_card_ids)

    def expire_due(self, teams: list[str], now_ms: int) -> ForbiddenWordState:
        return self._end_turn(teams) if self.phase == "running" and now_ms >= self.deadline_at_ms else self

    def _end_turn(self, teams: list[str]) -> ForbiddenWordState:
        ended = replace(self, phase="ready", current_card=None, started_at_ms=0, deadline_at_ms=0)
        if len(self.round_turns) < len(self.round_order):
            return ended
        scores = self.scores(teams)
        best = max(scores.values())
        leaders = [team for team in self.turn_order if scores[team] == best]
        if len(leaders) == 1:
            return replace(ended, phase="finished", winner_team=leaders[0])
        return replace(ended, sudden_death_round=self.sudden_death_round + 1, sudden_death_teams=leaders)

    def events_since(self, previous: ForbiddenWordState, teams: list[str]) -> list[DomainEvent]:
        if previous.phase == "ready" and self.phase == "running":
            return [TurnStarted(self.turns[-1].team)]
        if previous.phase != "running":
            return []
        sudden_death = (
            [SuddenDeathStarted(self.sudden_death_round, tuple(self.sudden_death_teams))]
            if self.sudden_death_round > previous.sudden_death_round
            else []
        )
        before, after = previous.turns[-1], self.turns[-1]
        events: list[DomainEvent] = []
        if len(after.found_words) > len(before.found_words):
            events.append(WordFound(after.team, after.found_words[-1]))
        if len(after.skipped_words) > len(before.skipped_words):
            events.append(WordSkipped(after.team, after.skipped_words[-1]))
        if self.phase != "running":
            events.append(TurnEnded(before.team, found_count=len(before.found_words)))
        return [*events, *sudden_death]
