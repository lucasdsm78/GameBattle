from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any, Optional

from domain.auction.models.auction_actions import AuctionActions
from domain.blindtest.models.blindtest_actions import BlindtestActions
from domain.bombe.models.bombe_actions import BombeActions
from domain.culture.models.culture_actions import CultureActions
from domain.flash_calc.models.flash_calc_actions import FlashCalcActions
from domain.forbidden_word.models.forbidden_word_actions import ForbiddenWordActions
from domain.game_night.events import (
    GameNightFinished,
    GameNightStarted,
    MancheFinished,
    MancheStarted,
    RankingRevealed,
)
from domain.game_night.models.active_round import ActiveRound
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from domain.game_night.models.session import GameSession
from domain.game_night.models.settings import (
    GameDefinition,
    GameRoundPlan,
    GameSettings,
    build_default_buzzer_keys,
)
from domain.game_night.services.round_sequence import (
    build_round_sequence,
    compute_ranking,
)
from domain.memory.models.memory_actions import MemoryActions
from domain.right_flag.models.right_flag_actions import RightFlagActions
from domain.seven_differences.models.seven_differences_actions import (
    SevenDifferencesActions,
)
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.clock import utc_now_iso
from domain.shared.services.scoring import TIE_LABEL
from domain.stopchrono.models.stopchrono_actions import StopChronoActions
from domain.vanishing_word.models.vanishing_word_actions import VanishingWordActions
from exceptions import GameConfigurationNotReadyError, InvalidGameConfigError

ALLOWED_STATUSES = frozenset({"configuring", "ready", "live", "finished"})

GameTransition = Callable[[Any], GameState]


@dataclass(slots=True)
class GameConfig(
    BlindtestActions,
    StopChronoActions,
    CultureActions,
    BombeActions,
    MemoryActions,
    SevenDifferencesActions,
    AuctionActions,
    ForbiddenWordActions,
    VanishingWordActions,
    FlashCalcActions,
    RightFlagActions,
):
    """Racine d'agrégat : configuration de la soirée et orchestration des manches.

    Chaque jeu range ses règles (`domain/<jeu>/models/<jeu>_state.py`) et ses actions
    (`domain/<jeu>/models/<jeu>_actions.py`, composées ici) dans son propre dossier. L'agrégat ne garde que
    l'orchestration : `_play` vérifie que le jeu ciblé est la manche en cours, applique la transition et clôt
    la manche dès qu'un vainqueur est désigné.

    Les événements de domaine produits par une commande s'accumulent dans `pending_events` (jamais
    persistés) jusqu'à ce que l'unité de travail les récupère avec `pull_events()`.
    """

    settings: GameSettings
    games: list[GameDefinition]
    rounds: list[GameRoundPlan]
    session: GameSession = field(default_factory=GameSession)
    status: str = "configuring"
    updated_at: str = ""
    pending_events: tuple[DomainEvent, ...] = field(default=(), compare=False, repr=False)

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

    def _record(self, *events: DomainEvent) -> GameConfig:
        return replace(self, pending_events=(*self.pending_events, *events)) if events else self

    def pull_events(self) -> tuple[GameConfig, tuple[DomainEvent, ...]]:
        """Sépare l'agrégat (prêt à persister) des événements produits depuis le dernier enregistrement."""
        return replace(self, pending_events=()), self.pending_events

    def _play(self, game_key: str, transition: GameTransition) -> GameConfig:
        active_round = self.session.active_round
        if self.status != "live" or active_round is None or active_round.game_key != game_key:
            raise InvalidGameConfigError(f"Aucune manche « {GAME_STATE_TYPES[game_key].label} » n’est en cours.")
        state = self.session.game(game_key)
        updated = transition(state)
        if updated is state:
            return self
        changes: dict[str, Any] = {game_key: updated}
        events = updated.events_since(state, self.teams)
        if updated.winner_team is not None and not self.session.manche_finished:
            changes.update(
                active_round=replace(active_round, completed=True), manche_finished=True, manche_winner=updated.winner_team
            )
            events.append(MancheFinished(self.session.round_index + 1, game_key, updated.winner_team))
        return self._replace_session(**changes)._record(*events)

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
        return prepared._record(GameNightStarted(total_rounds=len(sequence)))._start_manche(0)

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
        )._record(MancheStarted(number=index + 1, game_key=game_key))

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
        ranking = compute_ranking(self.teams, manches_won)
        leaders = tuple(entry["team"] for entry in reversed(ranking) if entry["rank"] == 1)
        return self._replace_session(
            status="finished",
            manches_won=manches_won,
            manche_finished=True,
            final_ranking=ranking,
            ranking_reveal_count=0,
        )._record(GameNightFinished(leaders=leaders))

    def reveal_next_ranking(self) -> GameConfig:
        if self.status != "finished" or not self.session.final_ranking:
            raise InvalidGameConfigError("Le classement final n'est pas encore disponible.")
        ranking = self.session.final_ranking
        count = min(self.session.ranking_reveal_count + 1, len(ranking))
        revealed = self._replace_session(ranking_reveal_count=count)
        if count == self.session.ranking_reveal_count:
            return revealed
        entry = ranking[count - 1]
        return revealed._record(RankingRevealed(team=entry["team"], rank=entry["rank"], manches_won=entry["manches_won"]))


_BUZZER_ACTIONS: dict[str, Callable[[GameConfig, str, int], GameConfig]] = {
    "blindtest": lambda config, team, now_ms: config.register_buzzer(team),
    "culture": lambda config, team, now_ms: config.register_culture_buzzer(team),
    "bombe": GameConfig.register_bombe_buzzer,
    "seven_differences": GameConfig.register_seven_differences_buzzer,
    "auction": GameConfig.register_auction_buzzer,
    "vanishing_word": GameConfig.register_vanishing_buzzer,
    "flash_calc": GameConfig.register_flash_calc_buzzer,
    "right_flag": GameConfig.register_right_flag_buzzer,
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
