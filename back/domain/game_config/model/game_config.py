from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import random
from typing import Any, Optional
from uuid import uuid4

from domain.game_config.exception.game_config_exception import GameConfigurationNotReadyError, InvalidGameConfigError
from domain.game_config.model.culture_questions import CULTURE_DIFFICULTIES, pick_one_culture_question

SUPPORTED_GAME_KEYS = {"blindtest", "stopchrono", "culture"}
ALLOWED_STATUSES = {"configuring", "ready", "live", "finished"}
TRACKS_PER_RANDOM_BLINDTEST_ROUND = 10
DEFAULT_BUZZER_KEYS = ["1", "2", "3", "4", "5", "6"]
PLAYBACK_STATES = {"stopped", "playing", "paused"}
STOPCHRONO_MIN_TARGET_MS = 7000
STOPCHRONO_MAX_TARGET_MS = 25000
STOPCHRONO_PHASES = {"idle", "running", "revealed", "finished"}
CULTURE_QUESTIONS_PER_ROUND = 10
CULTURE_PHASES = {"idle", "selecting", "question", "finished"}
ALLOWED_CULTURE_DIFFICULTIES = {"toutes", *CULTURE_DIFFICULTIES}
TIE_LABEL = "Égalité"
MAX_TOTAL_ROUNDS = 30


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
        # round_count n'est plus utilisé pour le séquençage (répartition équitable depuis total_rounds),
        # mais on garde le champ pour compatibilité — on borne juste sa valeur.
        if not 0 <= self.round_count <= MAX_TOTAL_ROUNDS:
            raise InvalidGameConfigError("Le nombre de manches par jeu est invalide.")


@dataclass(slots=True)
class GameSettings:
    game_title: str
    random_round_order: bool
    teams: list[str]
    buzzer_keys: list[str] = field(default_factory=list)
    total_rounds: int = 1
    culture_difficulty: str = "toutes"

    def validate(self) -> None:
        if len(self.game_title.strip()) < 3:
            raise InvalidGameConfigError("Le titre de la partie doit contenir au moins 3 caractères.")
        if not 1 <= self.total_rounds <= MAX_TOTAL_ROUNDS:
            raise InvalidGameConfigError(f"Le nombre de manches doit être compris entre 1 et {MAX_TOTAL_ROUNDS}.")
        if self.culture_difficulty not in ALLOWED_CULTURE_DIFFICULTIES:
            raise InvalidGameConfigError("La difficulté de culture générale est invalide.")
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


@dataclass(slots=True)
class StopChronoState:
    target_ms: int = 0
    phase: str = "idle"  # idle | running | revealed | finished
    current_team_index: int = 0
    started_at_ms: int = 0
    results: dict[str, int] = field(default_factory=dict)  # équipe -> temps stoppé (ms)
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None

    def validate(self, teams: list[str]) -> None:
        allowed_teams = {team.strip() for team in teams}
        if set(self.scores.keys()) - allowed_teams:
            raise InvalidGameConfigError("Les scores du stop chrono contiennent une équipe inconnue.")
        if set(self.results.keys()) - allowed_teams:
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


@dataclass(slots=True)
class CultureQuestion:
    id: str
    question: str
    answer: str
    explanation: str
    difficulty: str


@dataclass(slots=True)
class CultureState:
    phase: str = "idle"  # idle | selecting | question | finished
    current_index: int = 0
    total_questions: int = 0
    difficulty: str = "toutes"  # difficulté de la question courante (affichage)
    current_question: Optional[CultureQuestion] = None
    asked_questions: list[str] = field(default_factory=list)  # textes déjà posés (anti-répétition)
    current_buzzer_team: Optional[str] = None
    answered: bool = False
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None

    def validate(self, teams: list[str]) -> None:
        allowed_teams = {team.strip() for team in teams}
        if set(self.scores.keys()) - allowed_teams:
            raise InvalidGameConfigError("Les scores de culture générale contiennent une équipe inconnue.")
        if self.current_buzzer_team and self.current_buzzer_team not in allowed_teams:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if self.winner_team and self.winner_team not in allowed_teams and self.winner_team != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant de culture générale est inconnu.")
        if self.phase not in CULTURE_PHASES:
            raise InvalidGameConfigError("La phase de culture générale est invalide.")
        if self.current_index < 0:
            raise InvalidGameConfigError("L'index de question est invalide.")

    @property
    def questions_remaining(self) -> int:
        return max(self.total_questions - self.current_index, 0)


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
    stopchrono: StopChronoState = field(default_factory=StopChronoState)
    culture: CultureState = field(default_factory=CultureState)
    # Séquence des jeux pour chaque manche, déterminée au lancement et JAMAIS exposée aux apps
    # (le mobile et l'écran ne voient que la manche courante).
    round_sequence: list[str] = field(default_factory=list)
    round_index: int = 0
    total_rounds: int = 0
    manches_won: dict[str, int] = field(default_factory=dict)
    manche_finished: bool = False
    manche_winner: Optional[str] = None
    final_ranking: list[dict[str, Any]] = field(default_factory=list)
    ranking_reveal_count: int = 0
    updated_at: str = field(default_factory=utc_now_iso)

    def validate(self, teams: list[str]) -> None:
        allowed_teams = {team.strip() for team in teams}
        if self.active_round is not None:
            self.active_round.validate()
        self.blindtest.validate(teams)
        self.stopchrono.validate(teams)
        self.culture.validate(teams)
        if set(self.manches_won.keys()) - allowed_teams:
            raise InvalidGameConfigError("Le classement contient une équipe inconnue.")
        if self.manche_winner and self.manche_winner not in allowed_teams and self.manche_winner != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant de manche est inconnu.")
        if any(game_key not in SUPPORTED_GAME_KEYS for game_key in self.round_sequence):
            raise InvalidGameConfigError("La séquence de manches contient un jeu non supporté.")


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

        if not enabled_games:
            raise InvalidGameConfigError("Sélectionne au moins un jeu pour la partie.")

        # `rounds` est désormais optionnel (la séquence réelle est générée au lancement). On valide
        # seulement la cohérence des templates éventuellement fournis.
        round_ids = set()
        for round_config in self.rounds:
            round_config.validate()
            if round_config.game_key not in enabled_games:
                raise InvalidGameConfigError("Chaque manche doit appartenir à un jeu activé.")
            if round_config.id in round_ids:
                raise InvalidGameConfigError("Les identifiants de manche doivent être uniques.")
            round_ids.add(round_config.id)

        self.session.validate(self.settings.teams)

    def enabled_game_keys(self) -> list[str]:
        return [game.game_key for game in self.games if game.enabled]

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

    def _replace_session(self, *, status: Optional[str] = None, **session_changes: Any) -> "GameConfig":
        new_session = replace(self.session, updated_at=utc_now_iso(), **session_changes)
        return replace(self, session=new_session, status=(status or self.status), updated_at=utc_now_iso())

    def _build_manche_states(
        self, game_key: str, index: int
    ) -> tuple[ActiveRound, BlindtestState, StopChronoState, CultureState]:
        active_round = ActiveRound(
            round_id=f"{game_key}-manche-{index + 1}",
            label=f"Manche {index + 1}",
            game_key=game_key,
            order_index=index,
            completed=False,
        )
        teams_scores = {team: 0 for team in self.settings.teams}
        if game_key == "stopchrono":
            stopchrono = StopChronoState(
                target_ms=random.randint(STOPCHRONO_MIN_TARGET_MS // 1000, STOPCHRONO_MAX_TARGET_MS // 1000) * 1000,
                phase="idle",
                current_team_index=0,
                results={},
                scores=teams_scores,
            )
            return active_round, BlindtestState(), stopchrono, CultureState()
        if game_key == "culture":
            # Les questions ne sont PAS pré-tirées : le présentateur choisit la difficulté avant
            # chaque question, et une question est tirée à la demande.
            culture = CultureState(
                phase="idle",
                current_index=0,
                total_questions=CULTURE_QUESTIONS_PER_ROUND,
                difficulty="toutes",
                current_question=None,
                asked_questions=[],
                scores=teams_scores,
            )
            return active_round, BlindtestState(), StopChronoState(), culture
        blindtest = BlindtestState(
            round_id=active_round.round_id,
            total_tracks=TRACKS_PER_RANDOM_BLINDTEST_ROUND,
            current_track_index=1,
            scores=teams_scores,
            playback_state="stopped",
        )
        return active_round, blindtest, StopChronoState(), CultureState()

    def _start_manche(self, index: int) -> "GameConfig":
        game_key = self.session.round_sequence[index]
        active_round, blindtest, stopchrono, culture = self._build_manche_states(game_key, index)
        return self._replace_session(
            active_round=active_round,
            blindtest=blindtest,
            stopchrono=stopchrono,
            culture=culture,
            round_index=index,
            manche_finished=False,
            manche_winner=None,
            status="live",
        )

    def start_session(self) -> "GameConfig":
        pool = self.enabled_game_keys()
        if not pool:
            raise GameConfigurationNotReadyError("Aucun jeu sélectionné pour démarrer la partie.")
        sequence = build_round_sequence(pool, self.settings.total_rounds, self.settings.random_round_order)
        if not sequence:
            raise GameConfigurationNotReadyError("Impossible de générer les manches de la partie.")
        prepared = replace(
            self,
            session=GameSession(
                round_sequence=sequence,
                round_index=0,
                total_rounds=len(sequence),
                manches_won={team: 0 for team in self.settings.teams},
                manche_finished=False,
                manche_winner=None,
                final_ranking=[],
                ranking_reveal_count=0,
                updated_at=utc_now_iso(),
            ),
            status="live",
            updated_at=utc_now_iso(),
        )
        return prepared._start_manche(0)

    def with_blindtest_tracks(
        self,
        tracks: list[BlindtestTrack],
        playlist_name: str = "",
        playlist_source_url: str = "",
        playlist_provider: str = "manual",
    ) -> "GameConfig":
        if self.session.active_round is None or self.session.active_round.game_key != "blindtest":
            raise InvalidGameConfigError("Aucune manche blindtest active n'est disponible.")
        tracks = pick_blindtest_round_tracks(tracks, TRACKS_PER_RANDOM_BLINDTEST_ROUND)
        active_index = min(max(self.session.blindtest.current_track_index, 1), len(tracks)) if tracks else 0
        current_track = tracks[active_index - 1] if active_index else None
        blindtest_state = BlindtestState(
            round_id=self.session.blindtest.round_id,
            total_tracks=TRACKS_PER_RANDOM_BLINDTEST_ROUND,
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
        return self._replace_session(blindtest=blindtest_state)

    def register_buzzer(self, team: str) -> "GameConfig":
        if self.status != "live" or self.session.active_round is None or self.session.active_round.game_key != "blindtest":
            raise InvalidGameConfigError("Le buzz n'est disponible que pendant une manche blindtest en cours.")
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
        return self._replace_session(blindtest=blindtest_state)

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
        return self._replace_session(blindtest=blindtest_state)

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
        return self._replace_session(blindtest=blindtest_state)

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
        return self._replace_session(blindtest=blindtest_state)

    def advance_track(self) -> "GameConfig":
        blindtest = self.session.blindtest
        if not blindtest.tracks:
            raise InvalidGameConfigError("Aucune playlist blindtest n'est chargée.")
        if not blindtest.revealed:
            raise InvalidGameConfigError("Valide d'abord une bonne réponse avant de passer à la musique suivante.")

        next_index = blindtest.current_track_index + 1
        winner_team = blindtest.winner_team
        playback_state = "playing"
        current_track = None
        active_round = self.session.active_round
        manche_finished = self.session.manche_finished
        manche_winner = self.session.manche_winner

        if next_index > blindtest.total_tracks:
            playback_state = "stopped"
            max_score = max(blindtest.scores.values(), default=0)
            winners = [team for team, score in blindtest.scores.items() if score == max_score]
            winner_team = winners[0] if len(winners) == 1 else TIE_LABEL
            next_index = blindtest.total_tracks
            current_track = blindtest.current_track
            manche_finished = True
            manche_winner = winner_team
            if active_round is not None:
                active_round = replace(active_round, completed=True)
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
            revealed=blindtest.revealed if winner_team else False,
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
        return self._replace_session(
            active_round=active_round,
            blindtest=blindtest_state,
            manche_finished=manche_finished,
            manche_winner=manche_winner,
        )

    # --- Stop Chrono ---

    def _ensure_stopchrono_active(self) -> StopChronoState:
        if self.status != "live" or self.session.active_round is None or self.session.active_round.game_key != "stopchrono":
            raise InvalidGameConfigError("Aucune manche stop chrono n'est active.")
        return self.session.stopchrono

    def _with_stopchrono(
        self,
        chrono: StopChronoState,
        status: str,
        complete_round: bool = False,
        manche_winner: Optional[str] = None,
    ) -> "GameConfig":
        active_round = self.session.active_round
        changes: dict[str, Any] = {"stopchrono": chrono}
        if complete_round:
            if active_round is not None:
                changes["active_round"] = replace(active_round, completed=True)
            changes["manche_finished"] = True
            changes["manche_winner"] = manche_winner
        return self._replace_session(status=status, **changes)

    def start_chrono(self, now_ms: int) -> "GameConfig":
        chrono = self._ensure_stopchrono_active()
        if chrono.phase != "idle":
            raise InvalidGameConfigError("Le chrono ne peut démarrer que lorsqu'une équipe est prête.")
        return self._with_stopchrono(replace(chrono, phase="running", started_at_ms=int(now_ms)), status="live")

    def stop_chrono(self, now_ms: int) -> "GameConfig":
        chrono = self._ensure_stopchrono_active()
        if chrono.phase != "running":
            raise InvalidGameConfigError("Aucun chrono en cours à arrêter.")
        if chrono.current_team_index >= len(self.settings.teams):
            raise InvalidGameConfigError("Aucune équipe courante pour arrêter le chrono.")
        team = self.settings.teams[chrono.current_team_index]
        # Temps mesuré précisément en ms : le temps est affiché en secondes rondes côté UI,
        # mais l'écart à la cible est montré en ms pour départager finement.
        elapsed_ms = max(int(now_ms) - chrono.started_at_ms, 0)
        results = dict(chrono.results)
        results[team] = elapsed_ms
        return self._with_stopchrono(
            replace(chrono, phase="revealed", results=results, started_at_ms=0),
            status="live",
        )

    def next_chrono_team(self) -> "GameConfig":
        chrono = self._ensure_stopchrono_active()
        if chrono.phase != "revealed":
            raise InvalidGameConfigError("Valide d'abord le temps de l'équipe en cours.")
        next_index = chrono.current_team_index + 1
        if next_index < len(self.settings.teams):
            return self._with_stopchrono(
                replace(chrono, phase="idle", current_team_index=next_index, started_at_ms=0),
                status="live",
            )
        # Toutes les équipes ont joué : l'équipe la plus proche de la cible gagne (+1).
        deltas = {team: abs(elapsed - chrono.target_ms) for team, elapsed in chrono.results.items()}
        scores = {team: 0 for team in self.settings.teams}
        winner_team: Optional[str] = None
        if deltas:
            min_delta = min(deltas.values())
            winners = [team for team, delta in deltas.items() if delta == min_delta]
            for team in winners:
                scores[team] = 1
            winner_team = winners[0] if len(winners) == 1 else TIE_LABEL
        finished = replace(chrono, phase="finished", scores=scores, winner_team=winner_team, started_at_ms=0)
        # Fin de la MANCHE (pas de la partie) : on attend « Manche suivante ».
        return self._with_stopchrono(finished, status="live", complete_round=True, manche_winner=winner_team)

    # --- Culture générale ---

    def _ensure_culture_active(self) -> CultureState:
        if self.status != "live" or self.session.active_round is None or self.session.active_round.game_key != "culture":
            raise InvalidGameConfigError("Aucune manche de culture générale n'est active.")
        return self.session.culture

    def start_culture(self) -> "GameConfig":
        culture = self._ensure_culture_active()
        if culture.phase != "idle":
            raise InvalidGameConfigError("La manche de culture générale a déjà commencé.")
        # On passe au choix de la difficulté de la 1re question.
        return self._replace_session(
            culture=replace(culture, phase="selecting", current_index=1, current_question=None, current_buzzer_team=None, answered=False)
        )

    def select_culture_difficulty(self, difficulty: str) -> "GameConfig":
        culture = self._ensure_culture_active()
        if culture.phase != "selecting":
            raise InvalidGameConfigError("Le choix de la difficulté n'est pas disponible pour le moment.")
        picked = pick_one_culture_question(difficulty, set(culture.asked_questions))
        if picked is None:
            raise InvalidGameConfigError("Aucune question disponible pour cette difficulté.")
        question = CultureQuestion(
            id=f"culture-{self.session.active_round.round_id}-{culture.current_index}",
            question=picked["question"],
            answer=picked["answer"],
            explanation=picked["explanation"],
            difficulty=picked["difficulty"],
        )
        return self._replace_session(
            culture=replace(
                culture,
                phase="question",
                difficulty=question.difficulty,
                current_question=question,
                asked_questions=[*culture.asked_questions, question.question],
                current_buzzer_team=None,
                answered=False,
            )
        )

    def register_culture_buzzer(self, team: str) -> "GameConfig":
        culture = self._ensure_culture_active()
        if culture.phase != "question":
            raise InvalidGameConfigError("Aucune question n'est affichée pour buzzer.")
        if team not in culture.scores:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if culture.current_buzzer_team is not None and not culture.answered:
            raise InvalidGameConfigError("Un buzz est déjà en attente de validation.")
        if culture.answered:
            raise InvalidGameConfigError("La question a déjà été validée, passe à la suivante.")
        return self._replace_session(culture=replace(culture, current_buzzer_team=team))

    def answer_culture(self, is_correct: bool) -> "GameConfig":
        culture = self._ensure_culture_active()
        if culture.phase != "question":
            raise InvalidGameConfigError("Aucune question en cours pour valider une réponse.")
        if culture.current_buzzer_team is None:
            raise InvalidGameConfigError("Aucune équipe n'a buzzé pour valider une réponse.")
        if is_correct:
            scores = dict(culture.scores)
            scores[culture.current_buzzer_team] = scores.get(culture.current_buzzer_team, 0) + 1
            return self._replace_session(culture=replace(culture, scores=scores, answered=True))
        # Mauvaise réponse : on rouvre le buzz pour les autres équipes.
        return self._replace_session(culture=replace(culture, current_buzzer_team=None))

    def next_culture_question(self) -> "GameConfig":
        culture = self._ensure_culture_active()
        if culture.phase != "question":
            raise InvalidGameConfigError("Commence d'abord la manche de culture générale.")
        next_index = culture.current_index + 1
        if next_index <= culture.total_questions:
            # On revient au choix de la difficulté pour la question suivante.
            return self._replace_session(
                culture=replace(
                    culture,
                    phase="selecting",
                    current_index=next_index,
                    current_question=None,
                    current_buzzer_team=None,
                    answered=False,
                )
            )
        # Fin de la manche : l'équipe avec le plus de points l'emporte.
        max_score = max(culture.scores.values(), default=0)
        winners = [team for team, score in culture.scores.items() if score == max_score]
        winner = winners[0] if len(winners) == 1 else TIE_LABEL
        finished_culture = replace(culture, phase="finished", current_buzzer_team=None, winner_team=winner)
        active_round = self.session.active_round
        changes: dict[str, Any] = {"culture": finished_culture, "manche_finished": True, "manche_winner": winner}
        if active_round is not None:
            changes["active_round"] = replace(active_round, completed=True)
        return self._replace_session(status="live", **changes)

    # --- Orchestration des manches / classement final ---

    def next_manche(self) -> "GameConfig":
        if not self.session.manche_finished:
            raise InvalidGameConfigError("La manche en cours n'est pas terminée.")
        manches_won = dict(self.session.manches_won)
        winner = self.session.manche_winner
        if winner and winner != TIE_LABEL:
            manches_won[winner] = manches_won.get(winner, 0) + 1
        next_index = self.session.round_index + 1
        if next_index < self.session.total_rounds:
            advanced = self._replace_session(manches_won=manches_won)
            return advanced._start_manche(next_index)
        ranking = compute_ranking(self.settings.teams, manches_won)
        return self._replace_session(
            status="finished",
            manches_won=manches_won,
            manche_finished=True,
            final_ranking=ranking,
            ranking_reveal_count=0,
        )

    def reveal_next_ranking(self) -> "GameConfig":
        if self.status != "finished" or not self.session.final_ranking:
            raise InvalidGameConfigError("Le classement final n'est pas encore disponible.")
        total = len(self.session.final_ranking)
        next_count = min(self.session.ranking_reveal_count + 1, total)
        return self._replace_session(ranking_reveal_count=next_count)

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
                "stopchrono": {
                    **asdict(self.session.stopchrono),
                    "target_seconds": self.session.stopchrono.target_ms // 1000,
                    "current_team": (
                        self.settings.teams[self.session.stopchrono.current_team_index]
                        if 0 <= self.session.stopchrono.current_team_index < len(self.settings.teams)
                        else None
                    ),
                    "deltas_ms": {
                        team: abs(elapsed - self.session.stopchrono.target_ms)
                        for team, elapsed in self.session.stopchrono.results.items()
                    },
                },
                "culture": {
                    "phase": self.session.culture.phase,
                    "current_index": self.session.culture.current_index,
                    "total_questions": self.session.culture.total_questions,
                    "questions_remaining": self.session.culture.questions_remaining,
                    "difficulty": self.session.culture.difficulty,
                    "current_buzzer_team": self.session.culture.current_buzzer_team,
                    "answered": self.session.culture.answered,
                    "scores": dict(self.session.culture.scores),
                    "winner_team": self.session.culture.winner_team,
                    "asked_questions": list(self.session.culture.asked_questions),
                    # current_question contient la réponse + explication (affichées seulement sur le mobile).
                    "current_question": (
                        asdict(self.session.culture.current_question)
                        if self.session.culture.current_question
                        else None
                    ),
                },
                # Orchestration. `round_sequence` est persisté (round-trip DB) mais retiré du
                # payload envoyé aux clients par la couche WebSocket (les apps ne voient pas les prochains jeux).
                "round_sequence": list(self.session.round_sequence),
                "round_index": self.session.round_index,
                "total_rounds": self.session.total_rounds,
                "manche_number": min(self.session.round_index + 1, self.session.total_rounds) if self.session.total_rounds else 0,
                "manches_won": dict(self.session.manches_won),
                "manche_finished": self.session.manche_finished,
                "manche_winner": self.session.manche_winner,
                "final_ranking": list(self.session.final_ranking),
                "final_ranking_total": len(self.session.final_ranking),
                "ranking_reveal_count": self.session.ranking_reveal_count,
                "updated_at": self.session.updated_at,
            },
            "status": self.status,
            "updated_at": self.updated_at,
            "summary": {
                "round_count": self.session.total_rounds or self.settings.total_rounds,
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
            total_rounds=4,
        ),
        games=[
            GameDefinition(game_key="blindtest", label="Blindtest", enabled=True, round_count=0),
            GameDefinition(game_key="stopchrono", label="Stop Chrono", enabled=False, round_count=0),
            GameDefinition(game_key="culture", label="Culture générale", enabled=False, round_count=0),
        ],
        rounds=[],
        session=GameSession(updated_at=utc_now_iso()),
    ).with_timestamp()
    config.validate()
    return config


def build_round_sequence(pool: list[str], total: int, random_order: bool) -> list[str]:
    """Répartit `total` manches équitablement entre les jeux de `pool`.

    random_order=True : ordre mélangé en limitant les répétitions consécutives.
    random_order=False : ordre prévisible (round-robin).
    """
    if not pool or total <= 0:
        return []
    base, remainder = divmod(total, len(pool))
    counts = {key: base for key in pool}
    bonus_order = list(pool)
    if random_order:
        random.shuffle(bonus_order)
    for key in bonus_order[:remainder]:
        counts[key] += 1

    if not random_order:
        return _round_robin(pool, counts)
    return _shuffle_spread(counts)


def _round_robin(pool: list[str], counts: dict[str, int]) -> list[str]:
    remaining = dict(counts)
    sequence: list[str] = []
    while any(value > 0 for value in remaining.values()):
        for key in pool:
            if remaining[key] > 0:
                sequence.append(key)
                remaining[key] -= 1
    return sequence


def _shuffle_spread(counts: dict[str, int]) -> list[str]:
    remaining = dict(counts)
    sequence: list[str] = []

    while any(value > 0 for value in remaining.values()):
        previous = sequence[-1] if sequence else None
        candidates = [(game_key, count) for game_key, count in remaining.items() if count > 0 and game_key != previous]
        if not candidates:
            candidates = [(game_key, count) for game_key, count in remaining.items() if count > 0]

        max_remaining = max(count for _, count in candidates)
        best_candidates = [game_key for game_key, count in candidates if count == max_remaining]
        picked = random.choice(best_candidates)
        sequence.append(picked)
        remaining[picked] -= 1

    return sequence


def compute_ranking(teams: list[str], manches_won: dict[str, int]) -> list[dict[str, Any]]:
    """Classement ordonné du DERNIER au PREMIER (pour la révélation progressive)."""
    best_first = sorted(teams, key=lambda team: manches_won.get(team, 0), reverse=True)
    ranking: list[dict[str, Any]] = []
    previous_score: Optional[int] = None
    previous_rank = 0
    for index, team in enumerate(best_first):
        score = manches_won.get(team, 0)
        if score == previous_score:
            rank = previous_rank
        else:
            rank = index + 1
            previous_rank = rank
            previous_score = score
        ranking.append({"team": team, "manches_won": score, "rank": rank})
    # Inverse : dernier d'abord, premier en dernier.
    return list(reversed(ranking))


def pick_blindtest_round_tracks(tracks: list[BlindtestTrack], count: int) -> list[BlindtestTrack]:
    """Retourne exactement `count` titres pour une manche blindtest.

    Le nombre de titres joués par manche ne dépend jamais de la taille de la playlist Spotify :
    une playlist longue est mélangée puis tronquée, une playlist trop courte est refusée pour éviter
    des répétitions ou une fin de manche impossible à comprendre côté UX.
    """
    if len(tracks) < count:
        raise InvalidGameConfigError(f"La playlist blindtest doit contenir au moins {count} musiques.")
    shuffled = list(tracks)
    random.shuffle(shuffled)
    return shuffled[:count]


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


