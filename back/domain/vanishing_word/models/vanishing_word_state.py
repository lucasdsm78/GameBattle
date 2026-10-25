from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.scoring import zero_scores
from domain.vanishing_word.events import (
    VanishedWordRevealed,
    VanishingListShown,
    WordVanished,
)
from domain.vanishing_word.services.vanishing_word_catalog import (
    WORDS_PER_LIST,
    pick_vanishing_words,
)
from exceptions import InvalidGameConfigError

VANISHING_WORD_PHASES = frozenset({"idle", "memorizing", "vanished", "claimed", "revealed", "finished"})
VANISHING_WORD_MEMORIZATION_MS = 7_000
VANISHING_WORD_WINNING_SCORE = 5
HIDDEN_PHASES = frozenset({"vanished", "claimed"})


@dataclass(slots=True)
class VanishingWordState(GameState):
    """Une liste de 8 mots s'affiche, puis l'un d'eux disparaît : la première équipe à 5 mots trouvés gagne."""

    game_key: ClassVar[str] = "vanishing_word"
    label: ClassVar[str] = "Le mot qui disparaît"

    phase: str = "idle"
    round_number: int = 0
    words: list[str] = field(default_factory=list)  # la liste à mémoriser, dans son ordre d'affichage
    remaining_words: list[str] = field(default_factory=list)  # les 7 restants, remélangés
    vanished_word: str = ""
    reveal_at_ms: int = 0
    current_buzzer_team: Optional[str] = None
    excluded_teams: list[str] = field(default_factory=list)  # équipes qui se sont trompées sur cette liste
    round_winner: Optional[str] = None
    scores: dict[str, int] = field(default_factory=dict)
    used_words: list[str] = field(default_factory=list)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> VanishingWordState:
        return cls(scores=zero_scores(teams))

    def validate(self, teams: list[str]) -> None:
        allowed = set(teams)
        if self.phase not in VANISHING_WORD_PHASES:
            raise InvalidGameConfigError("La phase du Mot qui disparaît est invalide.")
        if self.phase == "idle" and not self.scores:
            return
        if set(self.scores) != allowed or any(
            not isinstance(score, int) or not 0 <= score <= VANISHING_WORD_WINNING_SCORE for score in self.scores.values()
        ):
            raise InvalidGameConfigError("Les scores du Mot qui disparaît sont invalides.")
        if sum(self.scores.values()) > self.round_number:
            raise InvalidGameConfigError("Le total des scores du Mot qui disparaît est incohérent.")
        if len(set(self.used_words)) != len(self.used_words):
            raise InvalidGameConfigError("Un mot du Mot qui disparaît a été tiré plusieurs fois.")
        if len(set(self.excluded_teams)) != len(self.excluded_teams) or set(self.excluded_teams) - allowed:
            raise InvalidGameConfigError("Les équipes exclues du Mot qui disparaît sont invalides.")
        if (self.current_buzzer_team and self.current_buzzer_team not in allowed) or (
            self.round_winner and self.round_winner not in allowed
        ):
            raise InvalidGameConfigError("Une équipe du Mot qui disparaît est inconnue.")
        if (self.phase == "finished") != (self.winner_team is not None):
            raise InvalidGameConfigError("Le vainqueur du Mot qui disparaît est incohérent.")
        if self.winner_team and self.scores.get(self.winner_team) != VANISHING_WORD_WINNING_SCORE:
            raise InvalidGameConfigError("Le vainqueur du Mot qui disparaît doit avoir trouvé 5 mots.")
        if self.phase == "idle":
            return
        if self.round_number < 1 or len(self.words) != WORDS_PER_LIST or len(set(self.words)) != WORDS_PER_LIST:
            raise InvalidGameConfigError("La liste du Mot qui disparaît est invalide.")
        if self.phase == "memorizing":
            if self.vanished_word or self.remaining_words or self.current_buzzer_team or self.excluded_teams or self.reveal_at_ms <= 0:
                raise InvalidGameConfigError("La mémorisation du Mot qui disparaît est invalide.")
            return
        if self.vanished_word not in self.words or sorted(self.remaining_words) != sorted(
            word for word in self.words if word != self.vanished_word
        ):
            raise InvalidGameConfigError("Le mot disparu est incohérent avec la liste.")
        if (self.phase == "claimed") != bool(self.current_buzzer_team) or self.current_buzzer_team in self.excluded_teams:
            raise InvalidGameConfigError("La prise de main du Mot qui disparaît est invalide.")

    def start_round(self, teams: list[str], now_ms: int) -> VanishingWordState:
        if self.phase not in {"idle", "revealed"}:
            raise InvalidGameConfigError("Une liste est déjà en cours.")
        words, restarted = pick_vanishing_words(self.used_words)
        return replace(
            self,
            phase="memorizing",
            round_number=self.round_number + 1,
            words=words,
            remaining_words=[],
            vanished_word="",
            reveal_at_ms=now_ms + VANISHING_WORD_MEMORIZATION_MS,
            current_buzzer_team=None,
            excluded_teams=[],
            round_winner=None,
            scores=dict(self.scores) or zero_scores(teams),
            used_words=[*([] if restarted else self.used_words), *words],
        )

    def _vanish(self) -> VanishingWordState:
        vanished = random.choice(self.words)
        remaining = [word for word in self.words if word != vanished]
        random.shuffle(remaining)
        return replace(self, phase="vanished", vanished_word=vanished, remaining_words=remaining)

    def expire_due(self, teams: list[str], now_ms: int) -> VanishingWordState:
        return self._vanish() if self.phase == "memorizing" and now_ms >= self.reveal_at_ms else self

    def register_buzzer(self, teams: list[str], team: str, now_ms: int) -> VanishingWordState:
        if team not in teams:
            raise InvalidGameConfigError("L’équipe qui buzze est inconnue.")
        state = self
        if state.phase == "memorizing":
            if now_ms < state.reveal_at_ms:
                raise InvalidGameConfigError("Attendez que le mot disparaisse avant de buzzer.")
            state = state._vanish()
        if state.phase != "vanished":
            raise InvalidGameConfigError("Les buzzers ne sont pas ouverts pour le moment.")
        if team in state.excluded_teams:
            raise InvalidGameConfigError("Cette équipe s’est déjà trompée sur cette liste.")
        return replace(state, phase="claimed", current_buzzer_team=team)

    def judge(self, teams: list[str], found: bool) -> VanishingWordState:
        if self.phase != "claimed" or not self.current_buzzer_team:
            raise InvalidGameConfigError("Aucune équipe n’a la main.")
        team = self.current_buzzer_team
        if found:
            scores = {**self.scores, team: self.scores.get(team, 0) + 1}
            winner = team if scores[team] >= VANISHING_WORD_WINNING_SCORE else None
            return replace(
                self,
                phase="finished" if winner else "revealed",
                scores=scores,
                current_buzzer_team=None,
                round_winner=team,
                winner_team=winner,
            )
        excluded = [*self.excluded_teams, team]
        everyone_failed = len(excluded) >= len(teams)
        return replace(self, phase="revealed" if everyone_failed else "vanished", excluded_teams=excluded, current_buzzer_team=None)

    def reveal(self) -> VanishingWordState:
        if self.phase not in HIDDEN_PHASES:
            raise InvalidGameConfigError("Aucun mot à révéler pour le moment.")
        return replace(self, phase="revealed", current_buzzer_team=None, round_winner=None)

    def events_since(self, previous: VanishingWordState, teams: list[str]) -> list[DomainEvent]:
        if self.round_number > previous.round_number:
            return [VanishingListShown(self.round_number)]
        events: list[DomainEvent] = []
        if previous.phase == "memorizing" and self.phase in HIDDEN_PHASES:
            events.append(WordVanished(self.round_number))
        if self.phase == "claimed" and self.current_buzzer_team and self.current_buzzer_team != previous.current_buzzer_team:
            events.append(BuzzerPressed(self.game_key, self.current_buzzer_team))
        judged_team = previous.current_buzzer_team if previous.phase == "claimed" else None
        if judged_team and self.round_winner == judged_team:
            events.append(AnswerJudged(self.game_key, judged_team, correct=True))
        elif judged_team and len(self.excluded_teams) > len(previous.excluded_teams):
            events.append(AnswerJudged(self.game_key, judged_team, correct=False))
        if previous.phase in HIDDEN_PHASES and self.phase in {"revealed", "finished"}:
            events.append(VanishedWordRevealed(self.vanished_word, found_by=self.round_winner))
        return events
