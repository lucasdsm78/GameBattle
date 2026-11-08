from __future__ import annotations

import pytest

from domain.accounts.models.password_policy import check_password, normalize_password
from domain.accounts.models.pseudo import Pseudo, check_pseudo_is_not_reserved
from exceptions import (
    InvalidAccountError,
)


@pytest.mark.parametrize("raw", ["Lucas", "Zoé-2", "le_boss_93", "abc", "A" * 20])
def test_valid_pseudos(raw: str) -> None:
    assert Pseudo.parse(f"  {raw} ").value == raw


@pytest.mark.parametrize("raw", ["ab", "A" * 21, "Lu cas", "Lucas!", "<script>", "Lucas😀", "Lu​cas", "Luсas"])
def test_invalid_pseudos_are_refused(raw: str) -> None:
    with pytest.raises(InvalidAccountError):
        Pseudo.parse(raw)


def test_a_pseudo_is_the_same_whatever_its_case_or_accent_encoding() -> None:
    assert Pseudo.parse("ZOÉ").key == Pseudo.parse("zoé").key


@pytest.mark.parametrize(("password", "message"), [
    ("court", "au moins 8"),
    ("x" * 129, "au plus 128"),
    ("Azerty123", "trop facile"),
    ("lucas2026!", "trop facile"),  # contient le pseudo
])
def test_weak_passwords_are_refused(password: str, message: str) -> None:
    with pytest.raises(InvalidAccountError, match=message):
        check_password(password, Pseudo("Lucas"))


def test_a_long_passphrase_with_spaces_is_accepted() -> None:
    check_password("  ma phrase de passe préférée  ", Pseudo("Lucas"))


@pytest.mark.parametrize("raw", ["Admin", "administrateur", "Modérateur_1", "GameBattle_Officiel", "modo", "Support", "Régie"])
def test_staff_like_pseudos_are_reserved_at_signup(raw: str) -> None:
    with pytest.raises(InvalidAccountError, match="réservé"):
        check_pseudo_is_not_reserved(Pseudo.parse(raw))


@pytest.mark.parametrize("raw", ["Modou", "supporter_psg", "Rootard", "Lucas"])
def test_ordinary_names_close_to_reserved_ones_stay_allowed(raw: str) -> None:
    check_pseudo_is_not_reserved(Pseudo.parse(raw))


def test_a_reserved_pseudo_still_loads_for_an_existing_account() -> None:
    assert Pseudo("Admin").value == "Admin"  # la réserve ne s'applique qu'aux nouvelles inscriptions


def test_passwords_are_compared_in_a_single_unicode_form() -> None:
    assert normalize_password("café au lait") == normalize_password("café au lait")
