from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from exceptions import InvalidPseudoError

PSEUDO_MIN_LENGTH = 3
PSEUDO_MAX_LENGTH = 20
# Lettres latines (accents compris), chiffres, « - » et « _ » : pas d'espace ni de caractère invisible ou trompeur.
_PSEUDO_PATTERN = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ_-]+")
# Personne ne doit pouvoir se faire passer pour l'équipe du jeu ou pour l'animateur d'une partie.
_RESERVED_PREFIXES = ("admin", "moderat", "modérat", "gamebattle")
_RESERVED_PSEUDOS = frozenset({
    "animateur", "modo", "officiel", "presentateur", "présentateur", "regie", "régie", "root", "staff", "support",
    "system", "systeme", "système",
})


@dataclass(frozen=True, slots=True)
class Pseudo:

    value: str

    def __post_init__(self) -> None:
        if not PSEUDO_MIN_LENGTH <= len(self.value) <= PSEUDO_MAX_LENGTH:
            raise InvalidPseudoError(f"Le pseudo doit faire entre {PSEUDO_MIN_LENGTH} et {PSEUDO_MAX_LENGTH} caractères.")
        if not _PSEUDO_PATTERN.fullmatch(self.value):
            raise InvalidPseudoError("Le pseudo ne peut contenir que des lettres, des chiffres, « - » et « _ ».")

    @classmethod
    def parse(cls, raw: str) -> Pseudo:
        # NFC : un « é » tapé en un ou deux caractères donne le même pseudo.
        return cls(unicodedata.normalize("NFC", raw.strip()))

    @property
    def key(self) -> str:
        return self.value.casefold()


def check_pseudo_is_not_reserved(pseudo: Pseudo) -> None:
    if pseudo.key in _RESERVED_PSEUDOS or pseudo.key.startswith(_RESERVED_PREFIXES):
        raise InvalidPseudoError("Ce pseudo est réservé : choisis-en un autre.")
