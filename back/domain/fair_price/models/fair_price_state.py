from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.fair_price.constants.fair_price_limits import FAIR_PRICE_HINTS
from domain.fair_price.constants.fair_price_phases import FAIR_PRICE_PHASES
from domain.fair_price.constants.fair_price_timing import FAIR_PRICE_TURN_MS
from domain.fair_price.events import PriceHintGiven, PriceTurnEnded, PriceTurnStarted
from domain.fair_price.models.price_item import PriceItem, PriceResult
from domain.fair_price.services.fair_price_catalog import (
    PRICE_BANDS_BY_ID,
    PRICE_ITEMS_BY_ID,
    pick_round_items,
)
from domain.shared.constants.scoring import TIE_LABEL
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from exceptions import InvalidGameConfigError


@dataclass(slots=True)
class FairPriceState(GameState):
    """Le juste prix : chaque équipe, à son tour, cherche le prix de son propre objet (« plus » / « moins »).

    Les objets d'une manche viennent de la même gamme de prix, avec des prix tous différents : une équipe ne
    peut pas reprendre la réponse de la précédente. L'équipe qui trouve le plus vite remporte la manche.
    """

    game_key: ClassVar[str] = "fair_price"
    label: ClassVar[str] = "Le juste prix"

    phase: str = "idle"
    band_id: str = ""
    turn_order: list[str] = field(default_factory=list)
    item_ids: list[str] = field(default_factory=list)  # un objet par équipe, dans l'ordre de passage
    results: list[PriceResult] = field(default_factory=list)
    started_at_ms: int = 0
    deadline_ms: int = 0
    proposals: int = 0  # réponses données pendant le tour : rend les décisions de la régie idempotentes
    hint: str = ""
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> FairPriceState:
        band, items = pick_round_items(len(teams))
        return cls(
            phase="ready",
            band_id=band.id,
            turn_order=random.sample(teams, len(teams)),
            item_ids=[item.id for item in items],
        )

    @property
    def current_index(self) -> int:
        return len(self.results)

    @property
    def current_team(self) -> Optional[str]:
        return self.turn_order[self.current_index] if self.phase in {"ready", "running"} else None

    @property
    def current_item(self) -> Optional[PriceItem]:
        return PRICE_ITEMS_BY_ID[self.item_ids[self.current_index]] if self.phase in {"ready", "running"} else None

    # --- Invariants ---

    def validate(self, teams: list[str]) -> None:
        if self.phase not in FAIR_PRICE_PHASES:
            raise InvalidGameConfigError("La phase du Juste prix est invalide.")
        if self.phase == "idle":
            return
        band = PRICE_BANDS_BY_ID.get(self.band_id)
        if sorted(self.turn_order) != sorted(teams) or len(self.item_ids) != len(teams):
            raise InvalidGameConfigError("L’ordre de passage du Juste prix est invalide.")
        if (
            band is None
            or len(set(self.item_ids)) != len(self.item_ids)
            or any(PRICE_ITEMS_BY_ID.get(item_id) not in band.items for item_id in self.item_ids)
        ):
            raise InvalidGameConfigError("Les objets du Juste prix sont invalides.")
        if [result.team for result in self.results] != self.turn_order[: len(self.results)] or [
            result.item_id for result in self.results
        ] != self.item_ids[: len(self.results)]:
            raise InvalidGameConfigError("Les résultats du Juste prix ne suivent pas l’ordre de passage.")
        if any(not 0 <= result.elapsed_ms <= FAIR_PRICE_TURN_MS or result.proposals < 0 for result in self.results):
            raise InvalidGameConfigError("Un temps du Juste prix est invalide.")
        if (self.phase == "finished") != (len(self.results) == len(self.turn_order)):
            raise InvalidGameConfigError("La fin du Juste prix est incohérente.")
        if self.phase == "finished" and self.winner_team != self._winner():
            raise InvalidGameConfigError("Le vainqueur du Juste prix est incohérent.")
        if self.phase == "running" and (self.deadline_ms - self.started_at_ms != FAIR_PRICE_TURN_MS or self.started_at_ms <= 0):
            raise InvalidGameConfigError("Le chrono du Juste prix est invalide.")
        if self.hint not in {"", *FAIR_PRICE_HINTS} or self.proposals < 0:
            raise InvalidGameConfigError("L’indice du Juste prix est invalide.")

    # --- Actions de la régie ---

    def start_turn(self, now_ms: int) -> FairPriceState:
        if self.phase != "ready":
            raise InvalidGameConfigError("Aucune équipe n’attend de jouer.")
        return replace(
            self, phase="running", started_at_ms=now_ms, deadline_ms=now_ms + FAIR_PRICE_TURN_MS, proposals=0, hint=""
        )

    def give_hint(self, direction: str, proposals: int, now_ms: int) -> FairPriceState:
        """« C'est plus » / « c'est moins » pour la réponse que l'équipe vient de donner."""
        if direction not in FAIR_PRICE_HINTS:
            raise InvalidGameConfigError("L’indice doit être « plus » ou « moins ».")
        if self.phase != "running" or proposals != self.proposals:
            return self  # double appui, ou tour déjà terminé
        if now_ms >= self.deadline_ms:
            return self._end_turn(found=False, now_ms=now_ms)
        return replace(self, proposals=self.proposals + 1, hint=direction)

    def mark_found(self, proposals: int, now_ms: int) -> FairPriceState:
        if self.phase != "running" or proposals != self.proposals:
            return self
        if now_ms >= self.deadline_ms:
            return self._end_turn(found=False, now_ms=now_ms)
        return replace(self, proposals=self.proposals + 1)._end_turn(found=True, now_ms=now_ms)

    def expire_due(self, teams: list[str], now_ms: int) -> FairPriceState:
        return self._end_turn(found=False, now_ms=now_ms) if self.phase == "running" and now_ms >= self.deadline_ms else self

    # --- Mécanique ---

    def _end_turn(self, *, found: bool, now_ms: int) -> FairPriceState:
        team, item = self.current_team, self.current_item
        assert team is not None and item is not None
        elapsed = min(max(now_ms - self.started_at_ms, 0), FAIR_PRICE_TURN_MS) if found else FAIR_PRICE_TURN_MS
        result = PriceResult(team=team, item_id=item.id, found=found, elapsed_ms=elapsed, proposals=self.proposals)
        ended = replace(self, results=[*self.results, result], started_at_ms=0, deadline_ms=0, hint="", proposals=0)
        if len(ended.results) < len(self.turn_order):
            return replace(ended, phase="ready")
        return replace(ended, phase="finished", winner_team=ended._winner())

    def _winner(self) -> str:
        """Le plus rapide parmi les équipes qui ont trouvé ; égalité si personne n'a trouvé."""
        found = sorted((result.elapsed_ms, order, result.team) for order, result in enumerate(self.results) if result.found)
        if not found:
            return TIE_LABEL
        if len(found) > 1 and found[0][0] == found[1][0]:
            return TIE_LABEL
        return found[0][2]

    def events_since(self, previous: FairPriceState, teams: list[str]) -> list[DomainEvent]:
        if previous.phase == "ready" and self.phase == "running" and self.current_team and self.current_item:
            return [PriceTurnStarted(self.current_team, self.current_item.name)]
        if self.phase == "running" and self.proposals > previous.proposals and self.current_team:
            return [PriceHintGiven(self.current_team, self.hint)]
        if len(self.results) > len(previous.results):
            result = self.results[-1]
            return [PriceTurnEnded(result.team, PRICE_ITEMS_BY_ID[result.item_id].price, result.found, result.elapsed_ms)]
        return []
