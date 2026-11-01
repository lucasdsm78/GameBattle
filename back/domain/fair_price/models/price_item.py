from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceItem:
    id: str
    name: str
    image: str  # fichier servi par le backend (`/media/fair-price/<image>`)
    price: int  # en euros TTC, prix constaté (voir `price_source` dans le catalogue)
    credit: str = ""  # auteur et licence de la photo, affichés sous l'image


@dataclass(frozen=True, slots=True)
class PriceBand:
    """Gamme de prix d'une manche : chaque équipe reçoit un objet différent de la même gamme."""

    id: str
    label: str
    items: tuple[PriceItem, ...]


@dataclass(frozen=True, slots=True)
class PriceResult:
    team: str
    item_id: str
    found: bool
    elapsed_ms: int
    proposals: int
