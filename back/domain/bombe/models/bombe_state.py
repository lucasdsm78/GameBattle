from __future__ import annotations

import random
import re
from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.bombe.events import BombeArmed, BombeDieRolling, BombeExploded, BombePassed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.scoring import zero_scores
from exceptions import InvalidGameConfigError

BOMBE_PHASES = frozenset({"idle", "awaiting_roll", "rolling", "running", "exploded"})
BOMBE_LETTERS = tuple("ABCDEFGHILMNOPRSTUV")
BOMBE_SOUND_ONSETS = tuple("BDFGKLMNPRSTV")
BOMBE_SOUND_VOWELS = ("A", "E", "I", "O", "OU")
BOMBE_SOUND_CODAS = ("", "", "L", "M", "N", "R", "S")
# Sons plus durs (groupes de consonnes, voyelles composées), choisis pour rester jouables à l'oral.
BOMBE_HARD_SOUND_RATIO = 0.4
BOMBE_HARD_SOUNDS = (
    "GRAN", "TRAN", "PLAN", "BLAN", "FRAN", "CHAN", "CRAN", "CLAN", "PRIN", "TRIN", "BRIN",
    "TROU", "GROU", "CLOU", "FLOU", "CHOU", "JOU", "BROU",
    "TROI", "CROI", "DROI", "FROI", "CHOI", "JOI", "PROI",
    "BLEU", "FLEU", "CHEU", "JEU", "PLEU", "PREU",
    "CRI", "PRI", "TRI", "BRI", "GRI", "PLI", "CLI",
    "TRO", "CRO", "GRO", "FLO", "GLO", "BRO", "PRO",
    "CHA", "CHI", "TRA", "GRA", "PLA", "BLA", "CLA", "DRA",
)
BOMBE_SOUND_PATTERN = re.compile(
    r"^(?:[BDFGKLMNPRSTV]|[BCDFGPT]R|[BCFGP]L|CH|J)(?:(?:OU|OI|EU|[AEIO])[LMNRS]?|AN|ON|IN)$"
)
BOMBE_DIE_RESULTS = ("TIC", "TAC", "BOUM")
BOMBE_DIE_ROLL_MS = 2_500
BOMBE_MIN_DURATION_MS = 30_000
BOMBE_MAX_DURATION_MS = 75_000


def generate_bombe_sound() -> str:
    """Compose un son court et prononçable ; quatre fois sur dix, tire un son plus dur."""
    if random.random() < BOMBE_HARD_SOUND_RATIO:
        return random.choice(BOMBE_HARD_SOUNDS)
    return f"{random.choice(BOMBE_SOUND_ONSETS)}{random.choice(BOMBE_SOUND_VOWELS)}{random.choice(BOMBE_SOUND_CODAS)}"


@dataclass(slots=True)
class BombeState(GameState):
    game_key: ClassVar[str] = "bombe"
    label: ClassVar[str] = "La Bombe"

    phase: str = "idle"
    letter: str = ""
    current_team_index: int = 0
    turn_history: list[int] = field(default_factory=list)
    started_at_ms: int = 0
    deadline_at_ms: int = 0
    exploded_team: Optional[str] = None
    winner_team: Optional[str] = None
    scores: dict[str, int] = field(default_factory=dict)
    eligible_team_indices: list[int] = field(default_factory=list)
    tiebreak_round: int = 0
    sound: str = ""
    die_result: str = ""
    roller_team_index: Optional[int] = None
    die_reveal_at_ms: int = 0

    def validate(self, teams: list[str]) -> None:
        allowed_teams = set(teams)
        if self.phase not in BOMBE_PHASES:
            raise InvalidGameConfigError("La phase de La Bombe est invalide.")
        if self.letter and self.letter not in BOMBE_LETTERS:
            raise InvalidGameConfigError("La lettre de La Bombe est invalide.")
        if self.current_team_index < 0 or (teams and self.current_team_index >= len(teams)):
            raise InvalidGameConfigError("L'équipe courante de La Bombe est invalide.")
        if any(index < 0 or index >= len(teams) for index in self.turn_history):
            raise InvalidGameConfigError("L'historique des équipes de La Bombe est invalide.")
        if self.started_at_ms < 0 or self.deadline_at_ms < 0:
            raise InvalidGameConfigError("Le timer de La Bombe est invalide.")
        if self.exploded_team and self.exploded_team not in allowed_teams:
            raise InvalidGameConfigError("L'équipe éliminée de La Bombe est inconnue.")
        if self.winner_team and self.winner_team not in allowed_teams:
            raise InvalidGameConfigError("Le gagnant de La Bombe est inconnu.")
        if set(self.scores) - allowed_teams or any(score < 0 for score in self.scores.values()):
            raise InvalidGameConfigError("Les pénalités de La Bombe sont invalides.")
        if len(set(self.eligible_team_indices)) != len(self.eligible_team_indices) or any(
            index < 0 or index >= len(teams) for index in self.eligible_team_indices
        ):
            raise InvalidGameConfigError("Les équipes en lice pour La Bombe sont invalides.")
        if self.phase == "running" and (
            len(self.eligible_team_indices) < 2 or self.current_team_index not in self.eligible_team_indices
        ):
            raise InvalidGameConfigError("La partie de La Bombe doit opposer au moins deux équipes en lice.")
        if self.tiebreak_round < 0:
            raise InvalidGameConfigError("Le numéro de départage de La Bombe est invalide.")
        if self.sound and not BOMBE_SOUND_PATTERN.fullmatch(self.sound):
            raise InvalidGameConfigError("Le son de La Bombe est invalide.")
        if self.die_result and self.die_result not in BOMBE_DIE_RESULTS:
            raise InvalidGameConfigError("Le résultat du dé de La Bombe est invalide.")
        if self.phase in {"awaiting_roll", "rolling"}:
            if self.roller_team_index is None:
                raise InvalidGameConfigError("Aucune équipe n'est désignée pour lancer le dé de La Bombe.")
            if self.roller_team_index not in self.eligible_team_indices:
                raise InvalidGameConfigError("Le lanceur du dé de La Bombe est invalide.")
        if self.phase == "rolling" and not self.die_result:
            raise InvalidGameConfigError("Le dé de La Bombe doit avoir un résultat secret.")
        if self.die_reveal_at_ms < 0:
            raise InvalidGameConfigError("Le timer du dé de La Bombe est invalide.")

    def start(self, teams: list[str], previous_roller: Optional[int]) -> BombeState:
        is_tiebreak = self.phase == "exploded" and self.winner_team is None
        if self.phase != "idle" and not is_tiebreak:
            raise InvalidGameConfigError("La Bombe a déjà démarré.")
        eligible = list(self.eligible_team_indices) if is_tiebreak else list(range(len(teams)))
        if len(eligible) < 2:
            raise InvalidGameConfigError("Au moins deux équipes sont requises pour lancer La Bombe.")
        if previous_roller is None:
            roller = eligible[random.randrange(len(eligible))]
        else:
            roller = next(
                index
                for offset in range(1, len(teams) + 1)
                if (index := (previous_roller + offset) % len(teams)) in eligible
            )
        return replace(
            self,
            phase="awaiting_roll",
            letter="",
            current_team_index=roller,
            turn_history=[],
            started_at_ms=0,
            deadline_at_ms=0,
            exploded_team=None,
            winner_team=None,
            scores=dict(self.scores) if is_tiebreak else zero_scores(teams),
            eligible_team_indices=eligible,
            tiebreak_round=self.tiebreak_round + 1 if is_tiebreak else 0,
            sound=generate_bombe_sound(),
            die_result="",
            roller_team_index=roller,
            die_reveal_at_ms=0,
        )

    def register_buzzer(self, teams: list[str], team: str, now_ms: int) -> BombeState:
        if self.phase == "awaiting_roll":
            roller_team = teams[self.roller_team_index or 0]
            if team != roller_team:
                raise InvalidGameConfigError(f"C'est à {roller_team} de lancer le dé.")
            return replace(
                self, phase="rolling", die_result=random.choice(BOMBE_DIE_RESULTS), die_reveal_at_ms=now_ms + BOMBE_DIE_ROLL_MS
            )
        if self.phase != "running":
            raise InvalidGameConfigError("La Bombe n'est pas en cours.")
        if now_ms >= self.deadline_at_ms:
            return self.explode(teams, now_ms)
        current_team = teams[self.current_team_index]
        if team != current_team:
            raise InvalidGameConfigError(f"C'est à {current_team} de jouer.")
        position = self.eligible_team_indices.index(self.current_team_index)
        next_index = self.eligible_team_indices[(position + 1) % len(self.eligible_team_indices)]
        return replace(self, current_team_index=next_index, turn_history=[*self.turn_history, next_index])

    def begin_after_roll(self, now_ms: int) -> BombeState:
        if self.phase == "running":
            return self
        if self.phase != "rolling":
            raise InvalidGameConfigError("Le dé de La Bombe n'est pas en cours.")
        if now_ms < self.die_reveal_at_ms:
            raise InvalidGameConfigError("Le dé de La Bombe tourne encore.")
        if self.roller_team_index is None:
            raise InvalidGameConfigError("Aucune équipe n'est désignée pour commencer La Bombe.")
        duration_ms = random.randint(BOMBE_MIN_DURATION_MS, BOMBE_MAX_DURATION_MS)
        return replace(
            self,
            phase="running",
            current_team_index=self.roller_team_index,
            turn_history=[self.roller_team_index],
            started_at_ms=now_ms,
            deadline_at_ms=now_ms + duration_ms,
        )

    def previous_team(self, teams: list[str], now_ms: int) -> BombeState:
        if self.phase != "running":
            raise InvalidGameConfigError("La Bombe n'est pas en cours.")
        if now_ms >= self.deadline_at_ms:
            return self.explode(teams, now_ms)
        if len(self.turn_history) < 2:
            raise InvalidGameConfigError("Aucune équipe précédente n'est disponible.")
        history = self.turn_history[:-1]
        return replace(self, current_team_index=history[-1], turn_history=history)

    def explode(self, teams: list[str], now_ms: int) -> BombeState:
        if self.phase == "exploded":
            return self
        if self.phase != "running":
            raise InvalidGameConfigError("La Bombe n'est pas en cours.")
        if now_ms < self.deadline_at_ms:
            raise InvalidGameConfigError("La Bombe n'a pas encore explosé.")
        exploded_team = teams[self.current_team_index]
        scores = {**self.scores, exploded_team: self.scores.get(exploded_team, 0) + 1}
        minimum = min(scores[teams[index]] for index in self.eligible_team_indices)
        contenders = [index for index in self.eligible_team_indices if scores[teams[index]] == minimum]
        return replace(
            self,
            phase="exploded",
            exploded_team=exploded_team,
            winner_team=teams[contenders[0]] if len(contenders) == 1 else None,
            scores=scores,
            eligible_team_indices=contenders,
        )

    def events_since(self, previous: BombeState, teams: list[str]) -> list[DomainEvent]:
        if previous.phase == "awaiting_roll" and self.phase == "rolling":
            return [BombeDieRolling(teams[self.roller_team_index or 0])]
        if previous.phase == "rolling" and self.phase == "running":
            return [BombeArmed(teams[self.current_team_index], die_result=self.die_result)]
        if previous.phase == "running" and self.phase == "exploded" and self.exploded_team:
            return [BombeExploded(self.exploded_team)]
        if previous.phase == self.phase == "running" and previous.current_team_index != self.current_team_index:
            return [BombePassed(from_team=teams[previous.current_team_index], to_team=teams[self.current_team_index])]
        return []
