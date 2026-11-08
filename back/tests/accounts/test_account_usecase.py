from __future__ import annotations

import asyncio
from typing import Optional

import pytest
from account_support import IP, PASSWORD, FakeHasher, build_use_case, make_credentials

from application.accounts.account_usecase import hash_session_token
from domain.accounts.models.player_session import (
    SESSION_RENEW_AFTER_MS,
    SESSION_TTL_MS,
)
from exceptions import (
    InvalidAccountError,
    InvalidCredentialsError,
    NotAuthenticatedError,
    PseudoAlreadyTakenError,
)


def test_registering_opens_a_session_and_never_stores_the_password() -> None:
    use_case, store, _ = build_use_case()
    signed_in = asyncio.run(use_case.register(make_credentials(), IP))

    (account,) = store.accounts.values()
    assert account.pseudo.value == "Lucas" and PASSWORD not in account.password_hash.split("$", 1)[0]
    assert list(store.sessions) == [hash_session_token(signed_in.token)]  # seule l'empreinte du jeton est gardée
    assert asyncio.run(use_case.current(signed_in.token)).account.pseudo == "Lucas"


def test_an_account_never_exists_without_its_session() -> None:
    use_case, store, _ = build_use_case(broken_sessions=True)

    with pytest.raises(RuntimeError):
        asyncio.run(use_case.register(make_credentials(), IP))
    assert store.accounts == {} and store.sessions == {}  # tout ou rien : le pseudo reste libre


def test_a_pseudo_cannot_be_taken_twice_whatever_its_case() -> None:
    use_case, *_ = build_use_case()
    asyncio.run(use_case.register(make_credentials("Lucas"), IP))

    with pytest.raises(PseudoAlreadyTakenError):
        asyncio.run(use_case.register(make_credentials("LUCAS"), "198.51.100.1"))


def test_login_with_the_right_password_works_whatever_the_pseudo_case() -> None:
    use_case, *_ = build_use_case()
    asyncio.run(use_case.register(make_credentials(), IP))

    assert asyncio.run(use_case.login(make_credentials("lucas"), IP)).account.pseudo == "Lucas"


def test_a_wrong_password_and_an_unknown_pseudo_are_indistinguishable() -> None:
    hasher = FakeHasher()
    use_case, *_ = build_use_case(hasher)
    asyncio.run(use_case.register(make_credentials(), IP))

    messages = []
    for credentials in (make_credentials(password="mauvais mot de passe"), make_credentials(pseudo="Inconnu"), make_credentials(pseudo="?!")):
        with pytest.raises(InvalidCredentialsError) as error:
            asyncio.run(use_case.login(credentials, IP))
        messages.append(error.value.message)
    assert len(set(messages)) == 1
    assert hasher.verifications == 3  # un pseudo inconnu coûte un hachage aussi : le temps de réponse ne trahit rien


def test_logout_and_expiry_end_the_session() -> None:
    use_case, store, clock = build_use_case()
    first = asyncio.run(use_case.register(make_credentials(), IP))
    asyncio.run(use_case.logout(first.token))
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(first.token))

    second = asyncio.run(use_case.login(make_credentials(), IP))
    clock.now += SESSION_TTL_MS
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(second.token))
    assert store.sessions == {}


def test_signing_in_again_replaces_the_previous_session_atomically() -> None:
    use_case, store, _ = build_use_case()
    first = asyncio.run(use_case.register(make_credentials(), IP))

    second = asyncio.run(use_case.login(make_credentials(), IP, replacing_token=first.token))
    assert list(store.sessions) == [hash_session_token(second.token)]


@pytest.mark.parametrize("token", [None, "", "x" * 129, "jeton-inconnu"])
def test_missing_or_forged_tokens_are_not_authenticated(token: Optional[str]) -> None:
    use_case, *_ = build_use_case()

    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(token))


def test_an_accented_password_works_whatever_the_keyboard_encoding() -> None:
    use_case, *_ = build_use_case()
    asyncio.run(use_case.register(make_credentials(password="café crème glacée"), IP))

    assert asyncio.run(use_case.login(make_credentials(password="café crème glacée"), IP)).account.pseudo == "Lucas"


def test_signing_up_with_a_reserved_pseudo_is_refused() -> None:
    use_case, store, _ = build_use_case()

    with pytest.raises(InvalidAccountError, match="réservé"):
        asyncio.run(use_case.register(make_credentials("Admin"), IP))
    assert store.accounts == {}


def test_an_active_player_session_slides_instead_of_expiring() -> None:
    use_case, store, clock = build_use_case()
    signed_in = asyncio.run(use_case.register(make_credentials(), IP))

    clock.now += SESSION_RENEW_AFTER_MS - 60_000
    assert asyncio.run(use_case.current(signed_in.token)).renewed_until_ms is None  # pas d'écriture à chaque visite
    clock.now += 2 * 60_000
    renewed = asyncio.run(use_case.current(signed_in.token))
    assert renewed.renewed_until_ms == clock.now + SESSION_TTL_MS
    assert store.sessions[hash_session_token(signed_in.token)].expires_at_ms == renewed.renewed_until_ms

    clock.now += SESSION_TTL_MS - 1
    assert asyncio.run(use_case.current(signed_in.token)).account.pseudo == "Lucas"


def test_an_outdated_hash_is_upgraded_at_the_next_login() -> None:
    hasher = FakeHasher(outdated=True)
    use_case, store, _ = build_use_case(hasher)
    asyncio.run(use_case.register(make_credentials(), IP))
    hasher.outdated = False

    asyncio.run(use_case.login(make_credentials(), IP))
    assert next(iter(store.accounts.values())).password_hash.startswith("fake-v2$")
