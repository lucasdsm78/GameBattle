from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Optional

from domain.models.games import GAME_STATE_TYPES
from domain.models.games.base import GameState
from domain.models.session import GameSession
from domain.models.settings import (
    GameDefinition,
    GameRoundPlan,
    GameSettings,
    build_default_buzzer_keys,
)
from domain.services.clock import utc_now_iso
from domain.services.round_sequence import build_round_sequence, compute_ranking
from domain.services.scoring import TIE_LABEL
from domain.vo.active_round import ActiveRound
from domain.vo.blindtest_track import BlindtestTrack
from exceptions import GameConfigurationNotReadyError, InvalidGameConfigError

ALLOWED_STATUSES = frozenset({"configuring", "ready", "live", "finished"})

GameTransition = Callable[[Any], GameState]


@dataclass(slots=True)
class GameConfig:
    """Racine d'agrégat : configuration de la soirée et orchestration des manches.

    Les règles de chaque jeu vivent dans `games/`. L'agrégat vérifie que le jeu ciblé est la manche en
    cours, applique la transition et clôt la manche dès qu'un vainqueur est désigné.
    """

    settings: GameSettings
    games: list[GameDefinition]
    rounds: list[GameRoundPlan]
    session: GameSession = field(default_factory=GameSession)
    status: str = "configuring"
    updated_at: str = ""

    @property
    def teams(self) -> list[str]:
        return self.settings.teams

    @property
    def round_count(self) -> int:
        return len(self.rounds)

    def validate(self) -> None:
        self.settings.validate()
        if self.status not in ALLOWED_STATUSES:
            raise InvalidGameConfigError("Le statut de la partie est invalide.")
        if not self.games:
            raise InvalidGameConfigError("Au moins un jeu doit être configuré.")
        game_keys: set[str] = set()
        for game in self.games:
            game.validate()
            if game.game_key in game_keys:
                raise InvalidGameConfigError("Chaque jeu ne peut être configuré qu'une seule fois.")
            game_keys.add(game.game_key)
        enabled_games = set(self.enabled_game_keys())
        if not enabled_games:
            raise InvalidGameConfigError("Sélectionne au moins un jeu pour la partie.")
        # `rounds` est optionnel (la séquence réelle est générée au lancement) : on valide sa cohérence.
        round_ids: set[str] = set()
        for round_config in self.rounds:
            round_config.validate()
            if round_config.game_key not in enabled_games:
                raise InvalidGameConfigError("Chaque manche doit appartenir à un jeu activé.")
            if round_config.id in round_ids:
                raise InvalidGameConfigError("Les identifiants de manche doivent être uniques.")
            round_ids.add(round_config.id)
        self.session.validate(self.teams)

    def enabled_game_keys(self) -> list[str]:
        return [game.game_key for game in self.games if game.enabled]

    def with_timestamp(self) -> GameConfig:
        return replace(self, updated_at=utc_now_iso())

    def ensure_can_launch(self) -> None:
        if not self.rounds:
            raise GameConfigurationNotReadyError("Aucune manche n'est configurée pour démarrer la partie.")

    def _replace_session(self, *, status: Optional[str] = None, **session_changes: Any) -> GameConfig:
        now = utc_now_iso()
        return replace(
            self, session=replace(self.session, updated_at=now, **session_changes), status=status or self.status, updated_at=now
        )

    def _play(self, game_key: str, transition: GameTransition) -> GameConfig:
        active_round = self.session.active_round
        if self.status != "live" or active_round is None or active_round.game_key != game_key:
            raise InvalidGameConfigError(f"Aucune manche « {GAME_STATE_TYPES[game_key].label} » n’est en cours.")
        state = self.session.game(game_key)
        updated = transition(state)
        if updated is state:
            return self
        changes: dict[str, Any] = {game_key: updated}
        if updated.winner_team is not None and not self.session.manche_finished:
            changes.update(
                active_round=replace(active_round, completed=True), manche_finished=True, manche_winner=updated.winner_team
            )
        return self._replace_session(**changes)

    # --- Blindtest ---

    def with_blindtest_tracks(
        self,
        tracks: list[BlindtestTrack],
        playlist_name: str = "",
        playlist_source_url: str = "",
        playlist_provider: str = "manual",
    ) -> GameConfig:
        return self._play(
            "blindtest",
            lambda game: game.with_tracks(
                tracks, playlist_name=playlist_name, playlist_source_url=playlist_source_url, playlist_provider=playlist_provider
            ),
        )

    def register_buzzer(self, team: str) -> GameConfig:
        return self._play("blindtest", lambda game: game.register_buzzer(team))

    def mark_answer(self, is_correct: bool) -> GameConfig:
        return self._play("blindtest", lambda game: game.mark_answer(is_correct))

    def control_playback(self, action: str, position_ms: Optional[int] = None) -> GameConfig:
        return self._play("blindtest", lambda game: game.control_playback(action, position_ms))

    def sync_playback(self, track_id: str, playback_state: str, position_ms: int, duration_ms: int = 0) -> GameConfig:
        return self._play("blindtest", lambda game: game.sync_playback(track_id, playback_state, position_ms, duration_ms))

    def advance_track(self) -> GameConfig:
        return self._play("blindtest", lambda game: game.advance_track())

    # --- Stop Chrono ---

    def start_chrono(self, now_ms: int) -> GameConfig:
        return self._play("stopchrono", lambda game: game.start(now_ms))

    def stop_chrono(self, now_ms: int) -> GameConfig:
        return self._play("stopchrono", lambda game: game.stop(self.teams, now_ms))

    def next_chrono_team(self) -> GameConfig:
        return self._play("stopchrono", lambda game: game.next_team(self.teams))

    # --- Culture générale ---

    def start_culture(self) -> GameConfig:
        return self._play("culture", lambda game: game.start())

    def select_culture_difficulty(self, difficulty: str) -> GameConfig:
        round_id = self.session.active_round.round_id if self.session.active_round else ""
        return self._play("culture", lambda game: game.select_difficulty(difficulty, round_id))

    def register_culture_buzzer(self, team: str) -> GameConfig:
        return self._play("culture", lambda game: game.register_buzzer(team))

    def answer_culture(self, is_correct: bool) -> GameConfig:
        return self._play("culture", lambda game: game.answer(is_correct))

    def next_culture_question(self) -> GameConfig:
        return self._play("culture", lambda game: game.next_question())

    # --- La Bombe ---

    def start_bombe(self, now_ms: int) -> GameConfig:
        started = self._play("bombe", lambda game: game.start(self.teams, self.session.last_bombe_roller_index))
        return started._replace_session(last_bombe_roller_index=started.session.bombe.roller_team_index)

    def register_bombe_buzzer(self, team: str, now_ms: int) -> GameConfig:
        return self._play("bombe", lambda game: game.register_buzzer(self.teams, team, now_ms))

    def begin_bombe_after_roll(self, now_ms: int) -> GameConfig:
        return self._play("bombe", lambda game: game.begin_after_roll(now_ms))

    def previous_bombe_team(self, now_ms: int) -> GameConfig:
        return self._play("bombe", lambda game: game.previous_team(self.teams, now_ms))

    def explode_bombe(self, now_ms: int) -> GameConfig:
        return self._play("bombe", lambda game: game.explode(self.teams, now_ms))

    # --- Mémoire en chaîne ---

    def start_memory(self) -> GameConfig:
        return self._play("memory", lambda game: game.start(self.teams))

    def next_memory_question(self) -> GameConfig:
        return self._play("memory", lambda game: game.next_question())

    def validate_memory_sequence(self) -> GameConfig:
        return self._play("memory", lambda game: game.validate_sequence())

    def disqualify_memory_team(self) -> GameConfig:
        return self._play("memory", lambda game: game.disqualify_team(self.teams))

    # --- Les 7 différences ---

    def start_seven_differences(self, now_ms: int) -> GameConfig:
        return self._play("seven_differences", lambda game: game.start(self.teams, now_ms))

    def open_seven_differences(self, now_ms: int) -> GameConfig:
        return self._play("seven_differences", lambda game: game.open(now_ms))

    def register_seven_differences_buzzer(self, team: str, now_ms: int) -> GameConfig:
        return self._play("seven_differences", lambda game: game.register_buzzer(self.teams, team, now_ms))

    def find_seven_difference(self, difference_id: str) -> GameConfig:
        return self._play("seven_differences", lambda game: game.find(self.teams, difference_id))

    def reject_seven_differences_answer(self) -> GameConfig:
        return self._play("seven_differences", lambda game: game.reject())

    # --- L’Enchère ---

    def start_auction(self) -> GameConfig:
        return self._play("auction", lambda game: game.start(self.teams))

    def register_auction_buzzer(self, team: str, now_ms: int) -> GameConfig:
        return self._play("auction", lambda game: game.register_buzzer(self.teams, team))

    def select_auction_bid(self, team: str, target_count: int) -> GameConfig:
        return self._play("auction", lambda game: game.select_bid(self.teams, team, target_count))

    def launch_auction_attempt(self, now_ms: int) -> GameConfig:
        return self._play("auction", lambda game: game.launch(now_ms))

    def change_auction_count(self, delta: int, now_ms: int) -> GameConfig:
        return self._play("auction", lambda game: game.change_count(self.teams, delta, now_ms))

    def expire_auction_attempt(self, now_ms: int) -> GameConfig:
        return self._play("auction", lambda game: game.expire(self.teams, now_ms))

    def next_auction_theme(self) -> GameConfig:
        return self._play("auction", lambda game: game.next_theme())

    # --- Le mot interdit ---

    def start_forbidden_word_turn(self, now_ms: int) -> GameConfig:
        return self._play("forbidden_word", lambda game: game.start_turn(now_ms))

    def resolve_forbidden_word_card(self, card_id: str, *, found: bool, now_ms: int) -> GameConfig:
        return self._play("forbidden_word", lambda game: game.resolve_card(self.teams, card_id, found=found, now_ms=now_ms))

    # --- Événements transverses ---

    def register_active_game_buzzer(self, team: str, now_ms: int) -> GameConfig:
        active_round = self.session.active_round
        if active_round is None:
            raise InvalidGameConfigError("Aucune manche active pour utiliser un buzzer.")
        buzz = _BUZZER_ACTIONS.get(active_round.game_key)
        if buzz is None:
            raise InvalidGameConfigError("Le jeu actif ne prend pas en charge ce buzzer matériel.")
        return buzz(self, team, now_ms)

    def expire_due_deadline(self, now_ms: int) -> GameConfig:
        """Clôt le chrono serveur échu de la manche active ; renvoie `self` s’il n’y a rien à faire."""
        active_round = self.session.active_round
        if self.status != "live" or active_round is None:
            return self
        return self._play(active_round.game_key, lambda game: game.expire_due(self.teams, now_ms))

    # --- Orchestration des manches / classement final ---

    def start_session(self) -> GameConfig:
        pool = self.enabled_game_keys()
        if not pool:
            raise GameConfigurationNotReadyError("Aucun jeu sélectionné pour démarrer la partie.")
        sequence = build_round_sequence(pool, self.settings.total_rounds, self.settings.random_round_order)
        if not sequence:
            raise GameConfigurationNotReadyError("Impossible de générer les manches de la partie.")
        prepared = replace(
            self,
            session=GameSession(round_sequence=sequence, total_rounds=len(sequence), manches_won={team: 0 for team in self.teams}),
            status="live",
            updated_at=utc_now_iso(),
        )
        return prepared._start_manche(0)

    def _start_manche(self, index: int) -> GameConfig:
        game_key = self.session.round_sequence[index]
        round_id = f"{game_key}-manche-{index + 1}"
        states: dict[str, GameState] = {key: state_type() for key, state_type in GAME_STATE_TYPES.items()}
        states[game_key] = GAME_STATE_TYPES[game_key].for_new_manche(self.teams, round_id)
        return self._replace_session(
            active_round=ActiveRound(round_id=round_id, label=f"Manche {index + 1}", game_key=game_key, order_index=index),
            round_index=index,
            manche_finished=False,
            manche_winner=None,
            status="live",
            **states,
        )

    def next_manche(self) -> GameConfig:
        if not self.session.manche_finished:
            raise InvalidGameConfigError("La manche en cours n'est pas terminée.")
        manches_won = dict(self.session.manches_won)
        winner = self.session.manche_winner
        if winner and winner != TIE_LABEL:
            manches_won[winner] = manches_won.get(winner, 0) + 1
        next_index = self.session.round_index + 1
        if next_index < self.session.total_rounds:
            return self._replace_session(manches_won=manches_won)._start_manche(next_index)
        return self._replace_session(
            status="finished",
            manches_won=manches_won,
            manche_finished=True,
            final_ranking=compute_ranking(self.teams, manches_won),
            ranking_reveal_count=0,
        )

    def reveal_next_ranking(self) -> GameConfig:
        if self.status != "finished" or not self.session.final_ranking:
            raise InvalidGameConfigError("Le classement final n'est pas encore disponible.")
        total = len(self.session.final_ranking)
        return self._replace_session(ranking_reveal_count=min(self.session.ranking_reveal_count + 1, total))

    # --- Sérialisation ---

    def to_dict(self) -> dict[str, Any]:
        session = self.session
        return {
            "settings": asdict(self.settings),
            "games": [asdict(game) for game in self.games],
            "rounds": [asdict(round_config) for round_config in self.rounds],
            "session": {
                "active_round": asdict(session.active_round) if session.active_round else None,
                **{game_key: session.game(game_key).to_payload(self.teams) for game_key in GAME_STATE_TYPES},
                "round_sequence": list(session.round_sequence),
                "round_index": session.round_index,
                "total_rounds": session.total_rounds,
                "manche_number": min(session.round_index + 1, session.total_rounds) if session.total_rounds else 0,
                "manches_won": dict(session.manches_won),
                "manche_finished": session.manche_finished,
                "manche_winner": session.manche_winner,
                "final_ranking": [dict(entry) for entry in session.final_ranking],
                "final_ranking_total": len(session.final_ranking),
                "ranking_reveal_count": session.ranking_reveal_count,
                "last_bombe_roller_index": session.last_bombe_roller_index,
                "updated_at": session.updated_at,
            },
            "status": self.status,
            "updated_at": self.updated_at,
            "summary": {
                "round_count": session.total_rounds or self.settings.total_rounds,
                "enabled_game_count": len(self.enabled_game_keys()),
                "teams": len(self.teams),
            },
        }

    def client_views(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Vues (régie, écran public) : sans données internes, et sans aucun secret pour l'écran public."""
        controller = self.to_dict()
        session = controller["session"]
        del session["round_sequence"]
        for game_key, state_type in GAME_STATE_TYPES.items():
            session[game_key] = state_type.shared_view(session[game_key])
        display_session = {
            **session,
            **{game_key: state_type.display_view(session[game_key]) for game_key, state_type in GAME_STATE_TYPES.items()},
        }
        return controller, {**controller, "session": display_session}


_BUZZER_ACTIONS: dict[str, Callable[[GameConfig, str, int], GameConfig]] = {
    "blindtest": lambda config, team, now_ms: config.register_buzzer(team),
    "culture": lambda config, team, now_ms: config.register_culture_buzzer(team),
    "bombe": GameConfig.register_bombe_buzzer,
    "seven_differences": GameConfig.register_seven_differences_buzzer,
    "auction": GameConfig.register_auction_buzzer,
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
            GameDefinition(game_key=game_key, label=state_type.label, enabled=game_key == "blindtest", round_count=0)
            for game_key, state_type in GAME_STATE_TYPES.items()
        ],
        rounds=[],
    ).with_timestamp()
    config.validate()
    return config
