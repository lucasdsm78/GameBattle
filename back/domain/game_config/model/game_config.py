from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import random
from typing import Any, Optional
from uuid import uuid4

from domain.game_config.exception.game_config_exception import GameConfigurationNotReadyError, InvalidGameConfigError

SUPPORTED_GAME_KEYS = {"blindtest"}
ALLOWED_STATUSES = {"configuring", "ready", "live", "finished"}
TRACKS_PER_RANDOM_BLINDTEST_ROUND = 10
DEFAULT_BUZZER_KEYS = ["1", "2", "3", "4", "5", "6"]
PLAYBACK_STATES = {"stopped", "playing", "paused"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class GameDefinition:
    game_key: str
    label: str
    enabled: bool
    round_count: int

    def validate(self) -> None:
        if self.game_key not in SUPPORTED_GAME_KEYS:
            raise InvalidGameConfigError(f"Jeu non supporté: {self.game_key}.")
        if len(self.label.strip()) < 2:
            raise InvalidGameConfigError("Chaque jeu doit avoir un libellé lisible.")
        if self.enabled and not 1 <= self.round_count <= 20:
            raise InvalidGameConfigError("Le nombre de manches par jeu doit être compris entre 1 et 20.")
        if not self.enabled and self.round_count != 0:
            raise InvalidGameConfigError("Un jeu désactivé doit avoir 0 manche configurée.")


@dataclass(slots=True)
class GameSettings:
    game_title: str
    random_round_order: bool
    teams: list[str]
    buzzer_keys: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if len(self.game_title.strip()) < 3:
            raise InvalidGameConfigError("Le titre de la partie doit contenir au moins 3 caractères.")
        if len(self.teams) < 2:
            raise InvalidGameConfigError("Au moins 2 équipes sont requises.")
        normalized_teams = [team.strip() for team in self.teams]
        if any(len(team) < 2 for team in normalized_teams):
            raise InvalidGameConfigError("Chaque équipe doit contenir au moins 2 caractères.")
        if len(set(team.lower() for team in normalized_teams)) != len(normalized_teams):
            raise InvalidGameConfigError("Les noms d'équipes doivent être uniques.")
        normalized_keys = [key.strip().lower() for key in self.buzzer_keys if key.strip()]
        if not normalized_keys:
            normalized_keys = build_default_buzzer_keys(len(normalized_teams))
        if len(normalized_keys) != len(normalized_teams):
            raise InvalidGameConfigError("Chaque équipe doit avoir une touche buzzer configurée.")
        if len(set(normalized_keys)) != len(normalized_keys):
            raise InvalidGameConfigError("Les touches buzzer doivent être uniques pour chaque équipe.")
        self.teams = normalized_teams
        self.buzzer_keys = normalized_keys


@dataclass(slots=True)
class GameRoundPlan:
    id: str
    label: str
    game_key: str
    planned_track_count: int
    buzzer_enabled: bool

    def validate(self) -> None:
        if len(self.id.strip()) < 3:
            raise InvalidGameConfigError("Chaque manche doit avoir un identifiant valide.")
        if len(self.label.strip()) < 2:
            raise InvalidGameConfigError("Chaque manche doit avoir un nom lisible.")
        if self.game_key not in SUPPORTED_GAME_KEYS:
            raise InvalidGameConfigError(f"Jeu de manche non supporté: {self.game_key}.")
        if not 1 <= self.planned_track_count <= 100:
            raise InvalidGameConfigError("Le nombre d'éléments prévus pour une manche doit être compris entre 1 et 100.")


@dataclass(slots=True)
class BlindtestTrack:
    track_id: str
    title: str
    artist: str
    preview_url: str = ""
    artwork_url: str = ""

    def validate(self) -> None:
        if len(self.track_id.strip()) < 2:
            raise InvalidGameConfigError("Chaque musique doit avoir un identifiant Spotify valide.")
        if len(self.title.strip()) < 1 or len(self.artist.strip()) < 1:
            raise InvalidGameConfigError("Chaque musique doit avoir un titre et un artiste.")
        if self.preview_url.strip() and len(self.preview_url.strip()) < 8:
            raise InvalidGameConfigError("L'URL de lecture d'une musique est invalide.")


@dataclass(slots=True)
class BlindtestState:
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

    def validate(self, teams: list[str]) -> None:
        allowed_teams = {team.strip() for team in teams}
        if set(self.scores.keys()) - allowed_teams:
            raise InvalidGameConfigError("Les scores du blindtest contiennent une équipe inconnue.")
        if self.current_buzzer_team and self.current_buzzer_team not in allowed_teams:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if self.winner_team and self.winner_team not in allowed_teams:
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
        return max(self.total_tracks - self.current_track_index, 0)


@dataclass(slots=True)
class ActiveRound:
    round_id: str
    label: str
    game_key: str
    order_index: int
    completed: bool = False

    def validate(self) -> None:
        if self.game_key not in SUPPORTED_GAME_KEYS:
            raise InvalidGameConfigError(f"Jeu actif non supporté: {self.game_key}.")
        if self.order_index < 0:
            raise InvalidGameConfigError("L'ordre de la manche active est invalide.")


@dataclass(slots=True)
class GameSession:
    active_round: Optional[ActiveRound] = None
    blindtest: BlindtestState = field(default_factory=BlindtestState)
    updated_at: str = field(default_factory=utc_now_iso)

    def validate(self, teams: list[str]) -> None:
        if self.active_round is not None:
            self.active_round.validate()
        self.blindtest.validate(teams)


@dataclass(slots=True)
class GameConfig:
    settings: GameSettings
    games: list[GameDefinition]
    rounds: list[GameRoundPlan]
    session: GameSession = field(default_factory=GameSession)
    status: str = "configuring"
    updated_at: str = ""

    def validate(self) -> None:
        self.settings.validate()
        if self.status not in ALLOWED_STATUSES:
            raise InvalidGameConfigError("Le statut de la partie est invalide.")
        if not self.games:
            raise InvalidGameConfigError("Au moins un jeu doit être configuré.")

        game_keys = set()
        enabled_games = set()
        for game in self.games:
            game.validate()
            if game.game_key in game_keys:
                raise InvalidGameConfigError("Chaque jeu ne peut être configuré qu'une seule fois.")
            game_keys.add(game.game_key)
            if game.enabled:
                enabled_games.add(game.game_key)

        if not 1 <= len(self.rounds) <= 12:
            raise InvalidGameConfigError("La partie doit contenir entre 1 et 12 manches.")

        round_ids = set()
        for round_config in self.rounds:
            round_config.validate()
            if round_config.game_key not in enabled_games:
                raise InvalidGameConfigError("Chaque manche doit appartenir à un jeu activé.")
            if round_config.id in round_ids:
                raise InvalidGameConfigError("Les identifiants de manche doivent être uniques.")
            round_ids.add(round_config.id)

        expected_rounds = sum(game.round_count for game in self.games if game.enabled)
        if expected_rounds != len(self.rounds):
            raise InvalidGameConfigError("Le nombre de manches ne correspond pas à la configuration par jeu.")

        self.session.validate(self.settings.teams)

    @property
    def round_count(self) -> int:
        return len(self.rounds)

    def with_timestamp(self) -> "GameConfig":
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=self.session,
            status=self.status,
            updated_at=utc_now_iso(),
        )

    def ensure_can_launch(self) -> None:
        if not self.rounds:
            raise GameConfigurationNotReadyError("Aucune manche n'est configurée pour démarrer la partie.")

    def start_session(self) -> "GameConfig":
        self.ensure_can_launch()
        selected_round = random.choice(self.rounds) if self.settings.random_round_order else self.rounds[0]
        active_round = ActiveRound(
            round_id=selected_round.id,
            label=selected_round.label,
            game_key=selected_round.game_key,
            order_index=0,
            completed=False,
        )
        blindtest_state = BlindtestState(
            round_id=selected_round.id,
            total_tracks=selected_round.planned_track_count,
            current_track_index=1,
            scores={team: 0 for team in self.settings.teams},
            playback_state="stopped",
        )
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=GameSession(active_round=active_round, blindtest=blindtest_state, updated_at=utc_now_iso()),
            status="live",
            updated_at=utc_now_iso(),
        )

    def with_blindtest_tracks(
        self,
        tracks: list[BlindtestTrack],
        playlist_name: str = "",
        playlist_source_url: str = "",
        playlist_provider: str = "manual",
    ) -> "GameConfig":
        if self.session.active_round is None or self.session.active_round.game_key != "blindtest":
            raise InvalidGameConfigError("Aucune manche blindtest active n'est disponible.")
        planned = next(
            (plan.planned_track_count for plan in self.rounds if plan.id == self.session.active_round.round_id),
            TRACKS_PER_RANDOM_BLINDTEST_ROUND,
        )
        if tracks:
            tracks = random.sample(tracks, min(planned, len(tracks)))
        active_index = min(max(self.session.blindtest.current_track_index, 1), len(tracks)) if tracks else 0
        current_track = tracks[active_index - 1] if active_index else None
        blindtest_state = BlindtestState(
            round_id=self.session.blindtest.round_id,
            total_tracks=len(tracks),
            current_track_index=active_index,
            current_track=current_track,
            current_buzzer_team=None,
            revealed=False,
            playback_state="playing" if tracks and self.status == "live" else "stopped",
            scores=dict(self.session.blindtest.scores),
            winner_team=self.session.blindtest.winner_team,
            tracks=tracks,
            playlist_name=playlist_name.strip(),
            playlist_source_url=playlist_source_url.strip(),
            playlist_provider=playlist_provider.strip(),
            playback_position_ms=0,
            playback_duration_ms=0,
            playback_updated_at=utc_now_iso(),
        )
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=GameSession(active_round=self.session.active_round, blindtest=blindtest_state, updated_at=utc_now_iso()),
            status=self.status,
            updated_at=utc_now_iso(),
        )

    def register_buzzer(self, team: str) -> "GameConfig":
        if self.status != "live" or self.session.active_round is None:
            raise InvalidGameConfigError("Le buzz n'est disponible que pendant une manche en cours.")
        active_round_config = next((round_config for round_config in self.rounds if round_config.id == self.session.active_round.round_id), None)
        if active_round_config is None:
            raise InvalidGameConfigError("La manche active est introuvable dans la configuration.")
        if not active_round_config.buzzer_enabled:
            raise InvalidGameConfigError("Les buzzers sont désactivés pour cette manche.")
        if self.session.blindtest.current_track is None:
            raise InvalidGameConfigError("Aucune musique n'est en lecture pour accepter un buzz.")
        if team not in self.session.blindtest.scores:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if self.session.blindtest.current_buzzer_team is not None and not self.session.blindtest.revealed:
            raise InvalidGameConfigError("Un buzz est déjà en attente de validation.")
        blindtest_state = BlindtestState(
            round_id=self.session.blindtest.round_id,
            total_tracks=self.session.blindtest.total_tracks,
            current_track_index=self.session.blindtest.current_track_index,
            current_track=self.session.blindtest.current_track,
            current_buzzer_team=team,
            revealed=self.session.blindtest.revealed,
            playback_state="paused",
            scores=dict(self.session.blindtest.scores),
            winner_team=self.session.blindtest.winner_team,
            tracks=list(self.session.blindtest.tracks),
            playlist_name=self.session.blindtest.playlist_name,
            playlist_source_url=self.session.blindtest.playlist_source_url,
            playlist_provider=self.session.blindtest.playlist_provider,
            playback_position_ms=self.session.blindtest.playback_position_ms,
            playback_duration_ms=self.session.blindtest.playback_duration_ms,
            playback_updated_at=utc_now_iso(),
        )
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=GameSession(active_round=self.session.active_round, blindtest=blindtest_state, updated_at=utc_now_iso()),
            status=self.status,
            updated_at=utc_now_iso(),
        )

    def mark_answer(self, is_correct: bool) -> "GameConfig":
        blindtest = self.session.blindtest
        if self.status != "live" or self.session.active_round is None:
            raise InvalidGameConfigError("Aucune manche blindtest n'est active.")
        if blindtest.current_track is None:
            raise InvalidGameConfigError("Aucune musique n'est chargée pour valider une réponse.")
        scores = dict(blindtest.scores)
        revealed = blindtest.revealed
        current_buzzer_team = blindtest.current_buzzer_team
        playback_state = blindtest.playback_state

        if is_correct:
            if current_buzzer_team is None:
                raise InvalidGameConfigError("Aucune équipe n'a buzzé pour valider une bonne réponse.")
            scores[current_buzzer_team] = scores.get(current_buzzer_team, 0) + 1
            revealed = True
            playback_state = "paused"
        else:
            current_buzzer_team = None
            playback_state = "playing"

        blindtest_state = BlindtestState(
            round_id=blindtest.round_id,
            total_tracks=blindtest.total_tracks,
            current_track_index=blindtest.current_track_index,
            current_track=blindtest.current_track,
            current_buzzer_team=current_buzzer_team,
            revealed=revealed,
            playback_state=playback_state,
            scores=scores,
            winner_team=blindtest.winner_team,
            tracks=list(blindtest.tracks),
            playlist_name=blindtest.playlist_name,
            playlist_source_url=blindtest.playlist_source_url,
            playlist_provider=blindtest.playlist_provider,
            playback_position_ms=blindtest.playback_position_ms,
            playback_duration_ms=blindtest.playback_duration_ms,
            playback_updated_at=utc_now_iso(),
        )
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=GameSession(active_round=self.session.active_round, blindtest=blindtest_state, updated_at=utc_now_iso()),
            status=self.status,
            updated_at=utc_now_iso(),
        )

    def control_playback(self, action: str, position_ms: Optional[int] = None) -> "GameConfig":
        blindtest = self.session.blindtest
        if self.status != "live" or self.session.active_round is None:
            raise InvalidGameConfigError("Aucune manche blindtest n'est active pour piloter la lecture.")
        if blindtest.current_track is None:
            raise InvalidGameConfigError("Aucune musique n'est chargée pour piloter la lecture.")

        normalized_action = action.strip().lower()
        if normalized_action not in {"play", "pause", "resume", "stop", "seek"}:
            raise InvalidGameConfigError("Commande de lecture blindtest non supportée.")

        next_position_ms = blindtest.playback_position_ms if position_ms is None else max(position_ms, 0)
        next_state = blindtest.playback_state
        if normalized_action in {"play", "resume"}:
            next_state = "playing"
        elif normalized_action == "pause":
            next_state = "paused"
        elif normalized_action == "stop":
            next_state = "stopped"
            next_position_ms = 0 if position_ms is None else next_position_ms

        if blindtest.playback_duration_ms > 0:
            next_position_ms = min(next_position_ms, blindtest.playback_duration_ms)

        blindtest_state = BlindtestState(
            round_id=blindtest.round_id,
            total_tracks=blindtest.total_tracks,
            current_track_index=blindtest.current_track_index,
            current_track=blindtest.current_track,
            current_buzzer_team=blindtest.current_buzzer_team,
            revealed=blindtest.revealed,
            playback_state=next_state,
            scores=dict(blindtest.scores),
            winner_team=blindtest.winner_team,
            tracks=list(blindtest.tracks),
            playlist_name=blindtest.playlist_name,
            playlist_source_url=blindtest.playlist_source_url,
            playlist_provider=blindtest.playlist_provider,
            playback_position_ms=next_position_ms,
            playback_duration_ms=blindtest.playback_duration_ms,
            playback_updated_at=utc_now_iso(),
        )
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=GameSession(active_round=self.session.active_round, blindtest=blindtest_state, updated_at=utc_now_iso()),
            status=self.status,
            updated_at=utc_now_iso(),
        )

    def sync_playback(self, track_id: str, playback_state: str, position_ms: int, duration_ms: int = 0) -> "GameConfig":
        blindtest = self.session.blindtest
        if self.session.active_round is None or self.session.active_round.game_key != "blindtest":
            raise InvalidGameConfigError("Aucune manche blindtest active n'est disponible pour synchroniser la lecture.")
        if blindtest.current_track is None:
            raise InvalidGameConfigError("Aucune musique active n'est disponible pour synchroniser la lecture.")
        if track_id.strip() and blindtest.current_track.track_id != track_id.strip():
            raise InvalidGameConfigError("La synchronisation audio ne correspond pas à la musique blindtest courante.")

        next_state = playback_state.strip().lower()
        if next_state not in PLAYBACK_STATES:
            raise InvalidGameConfigError("L'état de lecture synchronisé est invalide.")

        next_duration_ms = max(duration_ms, 0)
        next_position_ms = max(position_ms, 0)
        if next_duration_ms > 0:
            next_position_ms = min(next_position_ms, next_duration_ms)

        blindtest_state = BlindtestState(
            round_id=blindtest.round_id,
            total_tracks=blindtest.total_tracks,
            current_track_index=blindtest.current_track_index,
            current_track=blindtest.current_track,
            current_buzzer_team=blindtest.current_buzzer_team,
            revealed=blindtest.revealed,
            playback_state=next_state,
            scores=dict(blindtest.scores),
            winner_team=blindtest.winner_team,
            tracks=list(blindtest.tracks),
            playlist_name=blindtest.playlist_name,
            playlist_source_url=blindtest.playlist_source_url,
            playlist_provider=blindtest.playlist_provider,
            playback_position_ms=next_position_ms,
            playback_duration_ms=next_duration_ms,
            playback_updated_at=utc_now_iso(),
        )
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=GameSession(active_round=self.session.active_round, blindtest=blindtest_state, updated_at=utc_now_iso()),
            status=self.status,
            updated_at=utc_now_iso(),
        )

    def advance_track(self) -> "GameConfig":
        blindtest = self.session.blindtest
        if not blindtest.tracks:
            raise InvalidGameConfigError("Aucune playlist blindtest n'est chargée.")

        next_index = blindtest.current_track_index + 1
        winner_team = blindtest.winner_team
        playback_state = "playing"
        current_track = None
        status = self.status
        active_round = self.session.active_round

        if next_index > blindtest.total_tracks:
            status = "finished"
            playback_state = "stopped"
            max_score = max(blindtest.scores.values(), default=0)
            winners = [team for team, score in blindtest.scores.items() if score == max_score]
            winner_team = winners[0] if len(winners) == 1 else "Égalité"
            next_index = blindtest.total_tracks
            if active_round is not None:
                active_round = ActiveRound(
                    round_id=active_round.round_id,
                    label=active_round.label,
                    game_key=active_round.game_key,
                    order_index=active_round.order_index,
                    completed=True,
                )
        else:
            current_track = blindtest.tracks[next_index - 1]

        if current_track is None and blindtest.total_tracks > 0 and next_index >= 1 and next_index <= len(blindtest.tracks):
            current_track = blindtest.tracks[next_index - 1]

        blindtest_state = BlindtestState(
            round_id=blindtest.round_id,
            total_tracks=blindtest.total_tracks,
            current_track_index=next_index,
            current_track=current_track,
            current_buzzer_team=None,
            revealed=False,
            playback_state=playback_state,
            scores=dict(blindtest.scores),
            winner_team=winner_team,
            tracks=list(blindtest.tracks),
            playlist_name=blindtest.playlist_name,
            playlist_source_url=blindtest.playlist_source_url,
            playlist_provider=blindtest.playlist_provider,
            playback_position_ms=0,
            playback_duration_ms=0,
            playback_updated_at=utc_now_iso(),
        )
        return GameConfig(
            settings=self.settings,
            games=self.games,
            rounds=self.rounds,
            session=GameSession(active_round=active_round, blindtest=blindtest_state, updated_at=utc_now_iso()),
            status=status,
            updated_at=utc_now_iso(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "settings": asdict(self.settings),
            "games": [asdict(game) for game in self.games],
            "rounds": [asdict(round_config) for round_config in self.rounds],
            "session": {
                "active_round": asdict(self.session.active_round) if self.session.active_round else None,
                "blindtest": {
                    **asdict(self.session.blindtest),
                    "current_track": asdict(self.session.blindtest.current_track) if self.session.blindtest.current_track else None,
                    "tracks": [asdict(track) for track in self.session.blindtest.tracks],
                    "tracks_remaining": self.session.blindtest.tracks_remaining,
                },
                "updated_at": self.session.updated_at,
            },
            "status": self.status,
            "updated_at": self.updated_at,
            "summary": {
                "round_count": len(self.rounds),
                "enabled_game_count": len([game for game in self.games if game.enabled]),
                "teams": len(self.settings.teams),
            },
        }


def build_default_game_config() -> GameConfig:
    config = GameConfig(
        settings=GameSettings(
            game_title="GameBattle Night",
            random_round_order=True,
            teams=["Équipe Rouge", "Équipe Bleue"],
            buzzer_keys=build_default_buzzer_keys(2),
        ),
        games=[
            GameDefinition(
                game_key="blindtest",
                label="Blindtest",
                enabled=True,
                round_count=1,
            )
        ],
        rounds=[
            GameRoundPlan(
                id="blindtest-round-1",
                label="Blindtest aléatoire",
                game_key="blindtest",
                planned_track_count=TRACKS_PER_RANDOM_BLINDTEST_ROUND,
                buzzer_enabled=True,
            ),
        ],
        session=GameSession(
            blindtest=BlindtestState(scores={"Équipe Rouge": 0, "Équipe Bleue": 0}),
            updated_at=utc_now_iso(),
        ),
    ).with_timestamp()
    config.validate()
    return config


def build_default_buzzer_keys(team_count: int) -> list[str]:
    if team_count <= len(DEFAULT_BUZZER_KEYS):
        return DEFAULT_BUZZER_KEYS[:team_count]
    return [str(index + 1) for index in range(team_count)]


def build_blindtest_track(
    title: str,
    artist: str,
    preview_url: str,
    artwork_url: str = "",
    track_id: Optional[str] = None,
) -> BlindtestTrack:
    return BlindtestTrack(
        track_id=(track_id or f"track-{uuid4().hex[:12]}"),
        title=title,
        artist=artist,
        preview_url=preview_url,
        artwork_url=artwork_url,
    )


