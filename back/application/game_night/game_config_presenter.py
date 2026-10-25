from __future__ import annotations

from dataclasses import asdict
from typing import Any

from application.auction.auction_presenter import AuctionPresenter
from application.blindtest.blindtest_presenter import BlindtestPresenter
from application.bombe.bombe_presenter import BombePresenter
from application.culture.culture_presenter import CulturePresenter
from application.flash_calc.flash_calc_presenter import FlashCalcPresenter
from application.forbidden_word.forbidden_word_presenter import ForbiddenWordPresenter
from application.memory.memory_presenter import MemoryPresenter
from application.seven_differences.seven_differences_presenter import (
    SevenDifferencesPresenter,
)
from application.shared.game_presenter import GamePresenter
from application.stopchrono.stopchrono_presenter import StopChronoPresenter
from application.vanishing_word.vanishing_word_presenter import VanishingWordPresenter
from domain.game_night.models.game_config import GameConfig

GAME_PRESENTERS: dict[str, GamePresenter[Any]] = {
    "blindtest": BlindtestPresenter(),
    "stopchrono": StopChronoPresenter(),
    "culture": CulturePresenter(),
    "bombe": BombePresenter(),
    "memory": MemoryPresenter(),
    "seven_differences": SevenDifferencesPresenter(),
    "auction": AuctionPresenter(),
    "forbidden_word": ForbiddenWordPresenter(),
    "vanishing_word": VanishingWordPresenter(),
    "flash_calc": FlashCalcPresenter(),
}

ClientViews = tuple[dict[str, Any], dict[str, Any]]


def present_game_config(config: GameConfig) -> ClientViews:
    """Vues (régie, écran public) de la soirée.

    La séquence des manches n'est jamais exposée : les apps ne voient que la manche courante.
    """
    session = config.session
    teams = config.teams
    session_view: dict[str, Any] = {
        "active_round": asdict(session.active_round) if session.active_round else None,
        **{game_key: presenter.controller_view(session.game(game_key), teams) for game_key, presenter in GAME_PRESENTERS.items()},
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
    }
    controller = {
        "settings": asdict(config.settings),
        "games": [asdict(game) for game in config.games],
        "rounds": [asdict(round_config) for round_config in config.rounds],
        "session": session_view,
        "status": config.status,
        "updated_at": config.updated_at,
        "summary": {
            "round_count": session.total_rounds or config.settings.total_rounds,
            "enabled_game_count": len(config.enabled_game_keys()),
            "teams": len(teams),
        },
    }
    display_session = {
        **session_view,
        **{game_key: presenter.display_view(session_view[game_key]) for game_key, presenter in GAME_PRESENTERS.items()},
    }
    return controller, {**controller, "session": display_session}
