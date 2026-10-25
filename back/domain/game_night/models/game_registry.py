from domain.auction.models.auction_state import AuctionState
from domain.blindtest.models.blindtest_state import BlindtestState
from domain.bombe.models.bombe_state import BombeState
from domain.culture.models.culture_state import CultureState
from domain.flash_calc.models.flash_calc_state import FlashCalcState
from domain.forbidden_word.models.forbidden_word_state import ForbiddenWordState
from domain.golden_family.models.golden_family_state import GoldenFamilyState
from domain.memory.models.memory_state import MemoryState
from domain.right_flag.models.right_flag_state import RightFlagState
from domain.seven_differences.models.seven_differences_state import (
    SevenDifferencesState,
)
from domain.shared.models.game_state import GameState
from domain.stopchrono.models.stopchrono_state import StopChronoState
from domain.vanishing_word.models.vanishing_word_state import VanishingWordState

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
        VanishingWordState,
        FlashCalcState,
        RightFlagState,
        GoldenFamilyState,
    )
}

__all__ = [
    "GAME_STATE_TYPES",
    "AuctionState",
    "BlindtestState",
    "BombeState",
    "CultureState",
    "FlashCalcState",
    "ForbiddenWordState",
    "GoldenFamilyState",
    "MemoryState",
    "RightFlagState",
    "SevenDifferencesState",
    "StopChronoState",
    "VanishingWordState",
]
