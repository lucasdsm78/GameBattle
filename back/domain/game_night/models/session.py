from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from domain.auction.models.auction_state import AuctionState
from domain.blindtest.models.blindtest_state import BlindtestState
from domain.bombe.models.bombe_state import BombeState
from domain.culture.models.culture_state import CultureState
from domain.flash_calc.models.flash_calc_state import FlashCalcState
from domain.forbidden_word.models.forbidden_word_state import ForbiddenWordState
from domain.game_night.models.active_round import ActiveRound
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from domain.game_night.models.settings import SUPPORTED_GAME_KEYS
from domain.memory.models.memory_state import MemoryState
from domain.right_flag.models.right_flag_state import RightFlagState
from domain.seven_differences.models.seven_differences_state import (
    SevenDifferencesState,
)
from domain.shared.models.game_state import GameState
from domain.shared.services.clock import utc_now_iso
from domain.shared.services.scoring import TIE_LABEL
from domain.stopchrono.models.stopchrono_state import StopChronoState
from domain.vanishing_word.models.vanishing_word_state import VanishingWordState
from exceptions import InvalidGameConfigError


@dataclass(slots=True)
class GameSession:
    active_round: Optional[ActiveRound] = None
    blindtest: BlindtestState = field(default_factory=BlindtestState)
    stopchrono: StopChronoState = field(default_factory=StopChronoState)
    culture: CultureState = field(default_factory=CultureState)
    bombe: BombeState = field(default_factory=BombeState)
    memory: MemoryState = field(default_factory=MemoryState)
    seven_differences: SevenDifferencesState = field(default_factory=SevenDifferencesState)
    auction: AuctionState = field(default_factory=AuctionState)
    forbidden_word: ForbiddenWordState = field(default_factory=ForbiddenWordState)
    vanishing_word: VanishingWordState = field(default_factory=VanishingWordState)
    flash_calc: FlashCalcState = field(default_factory=FlashCalcState)
    right_flag: RightFlagState = field(default_factory=RightFlagState)
    # Persistée mais jamais exposée aux clients : les apps ne voient que la manche courante.
    round_sequence: list[str] = field(default_factory=list)
    round_index: int = 0
    total_rounds: int = 0
    manches_won: dict[str, int] = field(default_factory=dict)
    manche_finished: bool = False
    manche_winner: Optional[str] = None
    final_ranking: list[dict[str, Any]] = field(default_factory=list)
    ranking_reveal_count: int = 0
    last_bombe_roller_index: Optional[int] = None
    updated_at: str = field(default_factory=utc_now_iso)

    def game(self, game_key: str) -> GameState:
        return getattr(self, game_key)

    def validate(self, teams: list[str]) -> None:
        allowed_teams = set(teams)
        if self.active_round is not None:
            self.active_round.validate()
        for game_key in GAME_STATE_TYPES:
            self.game(game_key).validate(teams)
        if set(self.manches_won) - allowed_teams:
            raise InvalidGameConfigError("Le classement contient une équipe inconnue.")
        if self.manche_winner and self.manche_winner not in allowed_teams and self.manche_winner != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant de manche est inconnu.")
        if any(game_key not in SUPPORTED_GAME_KEYS for game_key in self.round_sequence):
            raise InvalidGameConfigError("La séquence de manches contient un jeu non supporté.")
        if self.last_bombe_roller_index is not None and not 0 <= self.last_bombe_roller_index < len(teams):
            raise InvalidGameConfigError("Le dernier lanceur du dé de La Bombe est invalide.")
