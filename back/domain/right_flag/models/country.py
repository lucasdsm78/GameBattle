from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Country:
    code: str  # ISO 3166-1 alpha-2 : identifie le drapeau
    name: str
    family: str  # drapeaux qui se ressemblent : la source des pièges
