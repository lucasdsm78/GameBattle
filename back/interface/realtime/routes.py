from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from application.auction.auction_commands import AuctionBidCommand
from application.blindtest.blindtest_commands import (
    PlaybackControlCommand,
    PlaybackSyncCommand,
    PlaylistLoadCommand,
    SpotifyPlaylistImportCommand,
    SpotifyTokenCommand,
)
from application.culture.culture_commands import CultureDifficultyCommand
from application.forbidden_word.forbidden_word_commands import ForbiddenWordCardCommand
from application.game_night.game_night_commands import GameConfigUpsertModel
from application.golden_family.golden_family_commands import (
    FamilyAnswerCommand,
    FamilyTurnCommand,
)
from application.seven_differences.seven_differences_commands import (
    SevenDifferenceFoundCommand,
)
from application.shared.commands import AnswerCommand, TeamCommand
from application.shared.snapshot import ClientRole
from application.use_cases import GameUseCases

CONTROLLER_ONLY = frozenset({ClientRole.CONTROLLER})
CONTROLLER_AND_DISPLAY = frozenset({ClientRole.CONTROLLER, ClientRole.DISPLAY})

RouteHandler = Callable[[GameUseCases, Any], Awaitable[Any]]


@dataclass(frozen=True, slots=True)
class Route:
    """Message WebSocket `event` → méthode de use case, avec son schéma d'entrée et les rôles autorisés."""

    event: str
    handler: RouteHandler
    payload_model: type[BaseModel] | None = None
    roles: frozenset[ClientRole] = CONTROLLER_ONLY


ROUTES: tuple[Route, ...] = (
    # Session
    Route("game.config.replace", lambda uc, cmd: uc.game_night.replace_config(cmd), GameConfigUpsertModel),
    Route("game.config.validate-and-launch", lambda uc, cmd: uc.game_night.validate_and_launch(cmd), GameConfigUpsertModel),
    Route("game.config.launch", lambda uc, _: uc.game_night.launch_game()),
    Route("game.next-manche", lambda uc, _: uc.game_night.next_manche()),
    Route("game.skip-opening", lambda uc, _: uc.game_night.skip_opening()),
    Route("ranking.reveal-next", lambda uc, _: uc.game_night.reveal_next_ranking()),
    # Blindtest
    Route("blindtest.playlist.load", lambda uc, cmd: uc.blindtest.load_playlist(cmd), PlaylistLoadCommand),
    Route("blindtest.playlist.import-spotify", lambda uc, cmd: uc.blindtest.import_spotify_playlist(cmd), SpotifyPlaylistImportCommand),
    Route("blindtest.playlist.reload", lambda uc, _: uc.blindtest.reload_default_playlist()),
    Route("blindtest.buzzer", lambda uc, cmd: uc.blindtest.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("blindtest.answer", lambda uc, cmd: uc.blindtest.answer(cmd), AnswerCommand),
    Route("blindtest.playback.control", lambda uc, cmd: uc.blindtest.control_playback(cmd), PlaybackControlCommand),
    Route("blindtest.playback.sync", lambda uc, cmd: uc.blindtest.sync_playback(cmd), PlaybackSyncCommand),
    Route("blindtest.next-track", lambda uc, _: uc.blindtest.next_track()),
    Route("spotify.user-token", lambda uc, cmd: uc.blindtest.set_spotify_user_token(cmd), SpotifyTokenCommand, CONTROLLER_AND_DISPLAY),
    # Stop Chrono
    Route("stopchrono.start", lambda uc, _: uc.stopchrono.start(), roles=CONTROLLER_AND_DISPLAY),
    Route("stopchrono.stop", lambda uc, _: uc.stopchrono.stop(), roles=CONTROLLER_AND_DISPLAY),
    Route("stopchrono.next-team", lambda uc, _: uc.stopchrono.next_team()),
    # Culture générale
    Route("culture.start", lambda uc, _: uc.culture.start()),
    Route("culture.select-difficulty", lambda uc, cmd: uc.culture.select_difficulty(cmd), CultureDifficultyCommand),
    Route("culture.buzzer", lambda uc, cmd: uc.culture.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("culture.answer", lambda uc, cmd: uc.culture.answer(cmd), AnswerCommand),
    Route("culture.reveal-answer", lambda uc, _: uc.culture.reveal_answer()),
    Route("culture.next-question", lambda uc, _: uc.culture.next_question()),
    # La Bombe
    Route("bombe.start", lambda uc, _: uc.bombe.start()),
    Route("bombe.buzzer", lambda uc, cmd: uc.bombe.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("bombe.begin-after-roll", lambda uc, _: uc.bombe.begin_after_roll(), roles=CONTROLLER_AND_DISPLAY),
    Route("bombe.previous-team", lambda uc, _: uc.bombe.previous_team()),
    Route("bombe.explode", lambda uc, _: uc.bombe.explode(), roles=CONTROLLER_AND_DISPLAY),
    # Mémoire en chaîne
    Route("memory.start", lambda uc, _: uc.memory.start()),
    Route("memory.next-question", lambda uc, _: uc.memory.next_question()),
    Route("memory.validate-sequence", lambda uc, _: uc.memory.validate_sequence()),
    Route("memory.disqualify-team", lambda uc, _: uc.memory.disqualify_team()),
    # Les 7 différences
    Route("seven-differences.start", lambda uc, _: uc.seven_differences.start()),
    Route("seven-differences.open", lambda uc, _: uc.seven_differences.open(), roles=CONTROLLER_AND_DISPLAY),
    Route("seven-differences.buzzer", lambda uc, cmd: uc.seven_differences.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("seven-differences.found", lambda uc, cmd: uc.seven_differences.mark_found(cmd), SevenDifferenceFoundCommand),
    Route("seven-differences.reject", lambda uc, _: uc.seven_differences.reject_answer()),
    # L’Enchère
    Route("auction.start", lambda uc, _: uc.auction.start()),
    Route("auction.buzzer", lambda uc, cmd: uc.auction.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("auction.select", lambda uc, cmd: uc.auction.select_bid(cmd), AuctionBidCommand),
    Route("auction.launch", lambda uc, _: uc.auction.launch()),
    Route("auction.increment", lambda uc, _: uc.auction.increment()),
    Route("auction.decrement", lambda uc, _: uc.auction.decrement()),
    Route("auction.next-theme", lambda uc, _: uc.auction.next_theme()),
    # Le mot interdit
    Route("forbidden-word.start-turn", lambda uc, _: uc.forbidden_word.start_turn()),
    Route("forbidden-word.found", lambda uc, cmd: uc.forbidden_word.mark_found(cmd), ForbiddenWordCardCommand),
    Route("forbidden-word.skip", lambda uc, cmd: uc.forbidden_word.skip(cmd), ForbiddenWordCardCommand),
    # Le mot qui disparaît
    Route("vanishing-word.start-round", lambda uc, _: uc.vanishing_word.start_round()),
    Route("vanishing-word.buzzer", lambda uc, cmd: uc.vanishing_word.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("vanishing-word.answer", lambda uc, cmd: uc.vanishing_word.answer(cmd), AnswerCommand),
    Route("vanishing-word.reveal", lambda uc, _: uc.vanishing_word.reveal()),
    # Calcul flash
    Route("flash-calc.start", lambda uc, _: uc.flash_calc.start()),
    Route("flash-calc.buzzer", lambda uc, cmd: uc.flash_calc.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("flash-calc.pause", lambda uc, _: uc.flash_calc.pause()),
    Route("flash-calc.resume", lambda uc, _: uc.flash_calc.resume()),
    # Le bon drapeau
    Route("right-flag.start", lambda uc, _: uc.right_flag.start()),
    Route("right-flag.buzzer", lambda uc, cmd: uc.right_flag.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("right-flag.pause", lambda uc, _: uc.right_flag.pause()),
    Route("right-flag.resume", lambda uc, _: uc.right_flag.resume()),
    # Une famille en or
    Route("golden-family.next-question", lambda uc, _: uc.golden_family.next_question()),
    Route("golden-family.buzzer", lambda uc, cmd: uc.golden_family.register_buzzer(cmd), TeamCommand, CONTROLLER_AND_DISPLAY),
    Route("golden-family.answer", lambda uc, cmd: uc.golden_family.give_answer(cmd), FamilyAnswerCommand),
    Route("golden-family.strike", lambda uc, cmd: uc.golden_family.strike(cmd), FamilyTurnCommand),
    Route("golden-family.reveal-board", lambda uc, _: uc.golden_family.reveal_board()),
)
