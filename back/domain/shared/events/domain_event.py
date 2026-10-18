from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Fait métier survenu lors d'une transition de l'agrégat.

    Un événement ne transporte jamais de secret (mot à faire deviner, réponse, résultat d'un dé qui
    roule) : il peut être diffusé à tous les clients, écran public compris.
    """

    name: ClassVar[str]
