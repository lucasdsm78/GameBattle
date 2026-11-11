from __future__ import annotations

import asyncio

import pytest
from account_support import (
    ATTEMPT_SECRET,
    IP,
    PASSWORD,
    AccountStore,
    Clock,
    FakeHasher,
    InMemoryAttempts,
    build_use_case,
    make_credentials,
)

from application.accounts.account_usecase import AccountUseCase
from application.shared.attempt_limit import AttemptLimit, enforce
from exceptions import (
    InvalidAccountError,
    InvalidCredentialsError,
    TooManyAttemptsError,
)
from infrastructure.database.database import Database
from infrastructure.repositories.accounts.account_unit_of_work import (
    SqlAccountUnitOfWork,
)


def test_repeated_failures_lock_the_pseudo_for_a_while() -> None:
    use_case, _, clock = build_use_case()
    asyncio.run(use_case.register(make_credentials(), IP))
    for attempt in range(5):
        with pytest.raises(InvalidCredentialsError):
            asyncio.run(use_case.login(make_credentials(password=f"essai {attempt} raté"), f"198.51.100.{attempt}"))

    with pytest.raises(TooManyAttemptsError) as locked:
        asyncio.run(use_case.login(make_credentials(), "198.51.100.99"))  # même le bon mot de passe attend
    assert 0 < locked.value.retry_after_seconds <= 15 * 60

    clock.now += 15 * 60_000
    assert asyncio.run(use_case.login(make_credentials(), IP)).account.pseudo == "Lucas"


def test_attempt_counters_survive_a_restart() -> None:
    first_process, store, clock = build_use_case()
    asyncio.run(first_process.register(make_credentials(), IP))
    for attempt in range(5):
        with pytest.raises(InvalidCredentialsError):
            asyncio.run(first_process.login(make_credentials(password=f"essai {attempt} raté"), IP))

    restarted, *_ = build_use_case(store=store, clock=clock)  # nouveau processus, même base
    with pytest.raises(TooManyAttemptsError):
        asyncio.run(restarted.login(make_credentials(), IP))


def test_one_address_cannot_create_accounts_in_bulk() -> None:
    use_case, *_ = build_use_case()
    for index in range(10):
        asyncio.run(use_case.register(make_credentials(f"Joueur{index}"), IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(use_case.register(make_credentials("Joueur10"), IP))


def test_refused_signups_consume_the_signup_limit_too() -> None:
    use_case, store, _ = build_use_case()
    asyncio.run(use_case.register(make_credentials("Lucas"), "198.51.100.1"))
    for attempt in range(10):  # pseudos pris, réservés, mots de passe faibles : chaque essai compte dès sa réception
        with pytest.raises(InvalidAccountError):
            asyncio.run(use_case.register(make_credentials(("LUCAS", "Admin", "Zoe")[attempt % 3], "motdepasse" if attempt % 3 == 2 else PASSWORD), IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(use_case.register(make_credentials("Valide"), IP))
    assert [account.pseudo.value for account in store.accounts.values()] == ["Lucas"]


def test_one_address_is_slowed_down_after_thirty_attempts_of_any_kind() -> None:
    use_case, *_ = build_use_case()
    for attempt in range(30):
        with pytest.raises(InvalidCredentialsError):
            asyncio.run(use_case.login(make_credentials(f"Inconnu{attempt}"), IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(use_case.register(make_credentials(), IP))


def test_a_reservation_counts_and_reports_in_one_step() -> None:
    counter, limit = InMemoryAttempts(AccountStore()), AttemptLimit("test", limit=2, window_ms=1_000)
    first, second, third = (asyncio.run(limit.reserve(counter, "joueur", at)) for at in (0, 10, 20))

    enforce(20, first, second)
    with pytest.raises(TooManyAttemptsError) as blocked:
        enforce(20, first, third)
    assert blocked.value.retry_after_seconds == 1
    assert not asyncio.run(limit.reserve(counter, "joueur", 1_000)).exceeded  # nouvelle fenêtre


def test_concurrent_logins_cannot_exceed_the_pseudo_limit(sqlite_database: Database) -> None:
    """Cinq connexions simultanées alors qu'il ne reste qu'un essai : une seule atteint Argon2."""
    hasher, clock = FakeHasher(), Clock()
    use_case = AccountUseCase(lambda: SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET), hasher, clock=clock)

    async def scenario() -> list[BaseException | object]:
        await use_case.register(make_credentials(), IP)
        for attempt in range(4):
            with pytest.raises(InvalidCredentialsError):
                await use_case.login(make_credentials(password=f"essai {attempt} raté"), f"198.51.100.{attempt}")
        hasher.verifications = 0
        return await asyncio.gather(
            *(use_case.login(make_credentials(password="encore raté"), f"203.0.113.{index}") for index in range(5)),
            return_exceptions=True,
        )

    outcomes = asyncio.run(scenario())
    assert sorted(type(outcome).__name__ for outcome in outcomes) == ["InvalidCredentialsError"] + ["TooManyAttemptsError"] * 4
    assert hasher.verifications == 1
