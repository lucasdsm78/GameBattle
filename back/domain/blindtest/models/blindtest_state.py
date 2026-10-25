from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional

from domain.blindtest.models.blindtest_track import BlindtestTrack
from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.clock import utc_now_iso
from domain.shared.services.scoring import TIE_LABEL, pick_round_winner, zero_scores
from exceptions import InvalidGameConfigError

TRACKS_PER_ROUND = 10
PLAYBACK_STATES = frozenset({"stopped", "playing", "paused"})
PLAYBACK_ACTIONS = frozenset({"play", "pause", "resume", "stop", "seek"})


def pick_round_tracks(tracks: list[BlindtestTrack], count: int) -> list[BlindtestTrack]:
    if len(tracks) < count:
        raise InvalidGameConfigError(f"La playlist blindtest doit contenir au moins {count} musiques.")
    shuffled = list(tracks)
    random.shuffle(shuffled)
    return shuffled[:count]


@dataclass(slots=True)
class BlindtestState(GameState):
    game_key: ClassVar[str] = "blindtest"
    label: ClassVar[str] = "Blindtest"

    round_id: str = ""
    total_tracks: int = 0
    current_track_index: int = 0
    current_track: Optional[BlindtestTrack] = None
    current_buzzer_team: Optional[str] = None
    revealed: bool = False
    playback_state: str = "stopped"
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None
    tracks: list[BlindtestTrack] = field(default_factory=list)
    playlist_name: str = ""
    playlist_source_url: str = ""
    playlist_provider: str = ""
    playback_position_ms: int = 0
    playback_duration_ms: int = 0
    playback_updated_at: str = field(default_factory=utc_now_iso)

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> BlindtestState:
        return cls(round_id=round_id, total_tracks=TRACKS_PER_ROUND, current_track_index=1, scores=zero_scores(teams))

    def validate(self, teams: list[str]) -> None:
        allowed_teams = set(teams)
        if set(self.scores) - allowed_teams:
            raise InvalidGameConfigError("Les scores du blindtest contiennent une équipe inconnue.")
        if self.current_buzzer_team and self.current_buzzer_team not in allowed_teams:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if self.winner_team and self.winner_team not in allowed_teams and self.winner_team != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant de manche est inconnu.")
        for track in self.tracks:
            track.validate()
        if self.current_track is not None:
            self.current_track.validate()
        if self.total_tracks < 0:
            raise InvalidGameConfigError("Le blindtest doit avoir un total de musiques positif.")
        if self.current_track_index < 0:
            raise InvalidGameConfigError("L'index de musique courante est invalide.")
        if self.playback_state not in PLAYBACK_STATES:
            raise InvalidGameConfigError("L'état de lecture blindtest est invalide.")
        if self.playback_position_ms < 0 or self.playback_duration_ms < 0:
            raise InvalidGameConfigError("Les informations de progression audio sont invalides.")

    @property
    def tracks_remaining(self) -> int:
        if self.winner_team or self.current_track is None:
            return 0
        return max(self.total_tracks - self.current_track_index + 1, 0)

    def _with_playback(self, **changes: Any) -> BlindtestState:
        return replace(self, playback_updated_at=utc_now_iso(), **changes)

    def with_tracks(
        self, tracks: list[BlindtestTrack], *, playlist_name: str, playlist_source_url: str, playlist_provider: str
    ) -> BlindtestState:
        picked = pick_round_tracks(tracks, TRACKS_PER_ROUND)
        index = min(max(self.current_track_index, 1), len(picked))
        return self._with_playback(
            total_tracks=TRACKS_PER_ROUND,
            current_track_index=index,
            current_track=picked[index - 1],
            current_buzzer_team=None,
            revealed=False,
            playback_state="playing",
            tracks=picked,
            playlist_name=playlist_name.strip(),
            playlist_source_url=playlist_source_url.strip(),
            playlist_provider=playlist_provider.strip(),
            playback_position_ms=0,
            playback_duration_ms=0,
        )

    def register_buzzer(self, team: str) -> BlindtestState:
        if self.current_track is None:
            raise InvalidGameConfigError("Aucune musique n'est en lecture pour accepter un buzz.")
        if team not in self.scores:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if self.current_buzzer_team is not None and not self.revealed:
            raise InvalidGameConfigError("Un buzz est déjà en attente de validation.")
        return self._with_playback(current_buzzer_team=team, playback_state="paused")

    def mark_answer(self, is_correct: bool) -> BlindtestState:
        if self.current_track is None:
            raise InvalidGameConfigError("Aucune musique n'est chargée pour valider une réponse.")
        if not is_correct:
            return self._with_playback(current_buzzer_team=None, playback_state="playing")
        if self.current_buzzer_team is None:
            raise InvalidGameConfigError("Aucune équipe n'a buzzé pour valider une bonne réponse.")
        if self.revealed:
            raise InvalidGameConfigError("La bonne réponse a déjà été validée.")
        scores = {**self.scores, self.current_buzzer_team: self.scores.get(self.current_buzzer_team, 0) + 1}
        return self._with_playback(scores=scores, revealed=True, playback_state="paused")

    def control_playback(self, action: str, position_ms: Optional[int]) -> BlindtestState:
        if self.current_track is None:
            raise InvalidGameConfigError("Aucune musique n'est chargée pour piloter la lecture.")
        action = action.strip().lower()
        if action not in PLAYBACK_ACTIONS:
            raise InvalidGameConfigError("Commande de lecture blindtest non supportée.")
        next_position_ms = self.playback_position_ms if position_ms is None else max(position_ms, 0)
        next_state = self.playback_state
        if action in {"play", "resume"}:
            next_state = "playing"
        elif action == "pause":
            next_state = "paused"
        elif action == "stop":
            next_state = "stopped"
            if position_ms is None:
                next_position_ms = 0
        if self.playback_duration_ms > 0:
            next_position_ms = min(next_position_ms, self.playback_duration_ms)
        return self._with_playback(playback_state=next_state, playback_position_ms=next_position_ms)

    def sync_playback(self, track_id: str, playback_state: str, position_ms: int, duration_ms: int) -> BlindtestState:
        if self.current_track is None:
            raise InvalidGameConfigError("Aucune musique active n'est disponible pour synchroniser la lecture.")
        if track_id.strip() and self.current_track.track_id != track_id.strip():
            raise InvalidGameConfigError("La synchronisation audio ne correspond pas à la musique blindtest courante.")
        next_state = playback_state.strip().lower()
        if next_state not in PLAYBACK_STATES:
            raise InvalidGameConfigError("L'état de lecture synchronisé est invalide.")
        next_duration_ms = max(duration_ms, 0)
        next_position_ms = max(position_ms, 0)
        if next_duration_ms > 0:
            next_position_ms = min(next_position_ms, next_duration_ms)
        return self._with_playback(
            playback_state=next_state, playback_position_ms=next_position_ms, playback_duration_ms=next_duration_ms
        )

    def advance_track(self) -> BlindtestState:
        if not self.tracks:
            raise InvalidGameConfigError("Aucune playlist blindtest n'est chargée.")
        if not self.revealed:
            raise InvalidGameConfigError("Valide d'abord une bonne réponse avant de passer à la musique suivante.")
        next_index = self.current_track_index + 1
        reset = {"current_buzzer_team": None, "playback_position_ms": 0, "playback_duration_ms": 0}
        if next_index > self.total_tracks:
            return self._with_playback(
                current_track_index=self.total_tracks,
                playback_state="stopped",
                winner_team=pick_round_winner(list(self.scores), self.scores),
                **reset,
            )
        return self._with_playback(
            current_track_index=next_index,
            current_track=self.tracks[next_index - 1],
            revealed=bool(self.winner_team),
            playback_state="playing",
            **reset,
        )

    def events_since(self, previous: BlindtestState, teams: list[str]) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self.current_buzzer_team and self.current_buzzer_team != previous.current_buzzer_team:
            events.append(BuzzerPressed("blindtest", self.current_buzzer_team))
        if previous.current_buzzer_team and not previous.revealed and self.current_track_index == previous.current_track_index:
            if self.revealed:
                events.append(AnswerJudged("blindtest", previous.current_buzzer_team, correct=True))
            elif self.current_buzzer_team is None:
                events.append(AnswerJudged("blindtest", previous.current_buzzer_team, correct=False))
        return events
