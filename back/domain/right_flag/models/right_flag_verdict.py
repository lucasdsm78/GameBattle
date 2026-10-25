from __future__ import annotations

from dataclasses import dataclass

from domain.shared.models.buzz_verdict import BuzzVerdict


@dataclass(frozen=True, slots=True)
class RightFlagVerdict(BuzzVerdict):
    flag_code: str  # le drapeau sur lequel l'équipe a buzzé
    flag_country: str
