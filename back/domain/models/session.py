from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from domain.models.games import (
    GAME_STATE_TYPES,
    AuctionState,
    BlindtestState,
    BombeState,
    CultureState,
    ForbiddenWordState,
    MemoryState,
    SevenDifferencesState,
    StopChronoState,
)
from domain.models.games.base import GameState
from domain.models.settings import SUPPORTED_GAME_KEYS
from domain.services.clock import utc_now_iso
from domain.services.scoring import TIE_LABEL
from domain.vo.active_round import ActiveRound
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
