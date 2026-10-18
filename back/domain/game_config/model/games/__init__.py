from domain.game_config.model.games.auction import AuctionState
from domain.game_config.model.games.blindtest import BlindtestState
from domain.game_config.model.games.bombe import BombeState
from domain.game_config.model.games.culture import CultureState
from domain.game_config.model.games.forbidden_word import ForbiddenWordState
from domain.game_config.model.games.memory import MemoryState
from domain.game_config.model.games.seven_differences import SevenDifferencesState
from domain.game_config.model.games.stopchrono import StopChronoState
from domain.game_config.model.shared import GameState

GAME_STATE_TYPES: dict[str, type[GameState]] = {
    state_type.game_key: state_type
    for state_type in (
        BlindtestState,
        StopChronoState,
        CultureState,
        BombeState,
        MemoryState,
        SevenDifferencesState,
        AuctionState,
        ForbiddenWordState,
    )
}

__all__ = [
    "GAME_STATE_TYPES",
    "AuctionState",
    "BlindtestState",
    "BombeState",
    "CultureState",
    "ForbiddenWordState",
    "MemoryState",
    "SevenDifferencesState",
    "StopChronoState",
]
