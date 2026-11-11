from __future__ import annotations

import unicodedata

from domain.accounts.constants.account_credentials import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from domain.accounts.models.pseudo import Pseudo
from exceptions import InvalidPasswordError

# Recommandation NIST 800-63B : une longueur minimale et le refus des mots de passe connus, sans règle de composition.
_COMMON_PASSWORDS = frozenset({
    "00000000", "11111111", "12345678", "123456789", "1234567890", "123123123", "87654321", "abcd1234", "abcdefgh",
    "azerty12", "azerty123", "azertyui", "azertyuiop", "bonjour1", "bonjour123", "chouchou", "doudou123", "football",
    "gamebattle", "iloveyou", "loulou123", "marseille", "motdepasse", "motdepasse1", "password", "password1",
    "qwerty123", "qwertyui", "qwertyuiop", "soleil123",
})


def normalize_password(raw: str) -> str:
    """NFKC (NIST 800-63B) : un « é » tapé en un ou deux caractères, selon le clavier, reste le même mot de passe."""
    return unicodedata.normalize("NFKC", raw)


def check_password(password: str, pseudo: Pseudo) -> None:
    """Refuse un mot de passe trop court, trop long, très répandu ou qui contient le pseudo."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise InvalidPasswordError(f"Le mot de passe doit faire au moins {PASSWORD_MIN_LENGTH} caractères.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise InvalidPasswordError(f"Le mot de passe doit faire au plus {PASSWORD_MAX_LENGTH} caractères.")
    folded = password.casefold()
    if folded in _COMMON_PASSWORDS or pseudo.key in folded:
        raise InvalidPasswordError("Ce mot de passe est trop facile à deviner : choisis-en un autre.")
