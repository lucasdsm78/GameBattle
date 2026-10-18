from domain.models.games.auction import AuctionState
from domain.models.games.base import GameState
from domain.models.games.blindtest import BlindtestState
from domain.models.games.bombe import BombeState
from domain.models.games.culture import CultureState
from domain.models.games.forbidden_word import ForbiddenWordState
from domain.models.games.memory import MemoryState
from domain.models.games.seven_differences import SevenDifferencesState
from domain.models.games.stopchrono import StopChronoState

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
