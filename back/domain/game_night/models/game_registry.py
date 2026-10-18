from domain.auction.models.auction_state import AuctionState
from domain.blindtest.models.blindtest_state import BlindtestState
from domain.bombe.models.bombe_state import BombeState
from domain.culture.models.culture_state import CultureState
from domain.forbidden_word.models.forbidden_word_state import ForbiddenWordState
from domain.memory.models.memory_state import MemoryState
from domain.seven_differences.models.seven_differences_state import (
    SevenDifferencesState,
)
from domain.shared.models.game_state import GameState
from domain.stopchrono.models.stopchrono_state import StopChronoState

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
