from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any, Optional

from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.games import (
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
from domain.game_config.model.settings import SUPPORTED_GAME_KEYS
from domain.game_config.model.shared import TIE_LABEL, GameState, utc_now_iso


@dataclass(slots=True)
class ActiveRound:
    round_id: str
    label: str
    game_key: str
    order_index: int
    completed: bool = False

    def validate(self) -> None:
        if self.game_key not in SUPPORTED_GAME_KEYS:
            raise InvalidGameConfigError(f"Jeu actif non supporté: {self.game_key}.")
        if self.order_index < 0:
            raise InvalidGameConfigError("L'ordre de la manche active est invalide.")


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


def build_round_sequence(pool: list[str], total: int, random_order: bool) -> list[str]:
    """Répartit `total` manches équitablement entre les jeux de `pool`.

    random_order=True : ordre mélangé en limitant les répétitions consécutives.
    random_order=False : ordre prévisible (round-robin).
    """
    if not pool or total <= 0:
        return []
    base, remainder = divmod(total, len(pool))
    counts = {key: base for key in pool}
    bonus_order = list(pool)
    if random_order:
        random.shuffle(bonus_order)
    for key in bonus_order[:remainder]:
        counts[key] += 1
    return _shuffle_spread(counts) if random_order else _round_robin(pool, counts)


def _round_robin(pool: list[str], counts: dict[str, int]) -> list[str]:
    remaining = dict(counts)
    sequence: list[str] = []
    while any(remaining.values()):
        for key in pool:
            if remaining[key] > 0:
                sequence.append(key)
                remaining[key] -= 1
    return sequence


def _shuffle_spread(counts: dict[str, int]) -> list[str]:
    remaining = dict(counts)
    sequence: list[str] = []
    while any(remaining.values()):
        previous = sequence[-1] if sequence else None
        candidates = [(key, count) for key, count in remaining.items() if count > 0 and key != previous]
        if not candidates:
            candidates = [(key, count) for key, count in remaining.items() if count > 0]
        max_remaining = max(count for _, count in candidates)
        picked = random.choice([key for key, count in candidates if count == max_remaining])
        sequence.append(picked)
        remaining[picked] -= 1
    return sequence


def compute_ranking(teams: list[str], manches_won: dict[str, int]) -> list[dict[str, Any]]:
    """Classement ordonné du DERNIER au PREMIER, pour la révélation progressive."""
    best_first = sorted(teams, key=lambda team: manches_won.get(team, 0), reverse=True)
    ranking: list[dict[str, Any]] = []
    previous_score: Optional[int] = None
    previous_rank = 0
    for index, team in enumerate(best_first):
        score = manches_won.get(team, 0)
        if score != previous_score:
            previous_rank = index + 1
            previous_score = score
        ranking.append({"team": team, "manches_won": score, "rank": previous_rank})
    return list(reversed(ranking))
