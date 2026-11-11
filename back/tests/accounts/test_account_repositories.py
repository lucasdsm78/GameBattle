from __future__ import annotations

import asyncio
import hashlib

import pytest
from account_support import (
    ATTEMPT_SECRET,
    IP,
    Clock,
    FakeHasher,
    make_credentials,
)
from sqlalchemy import func, select

from application.accounts.account_command_usecase import AccountCommandUseCase
from application.accounts.account_query_usecase import AccountQueryUseCase
from application.shared.attempt_counter import AttemptWindow
from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.player_session import (
    SESSION_TTL_MS,
    PlayerSession,
)
from domain.accounts.models.pseudo import Pseudo
from exceptions import (
    PseudoAlreadyTakenError,
)
from infrastructure.database.accounts.player_account_model import (
    PlayerAccountModel,
)
from infrastructure.database.database import Base, Database
from infrastructure.database.rate_limiting.attempt_model import AuthAttemptModel
from infrastructure.repositories.accounts.account_unit_of_work import (
    SqlAccountUnitOfWork,
)
from infrastructure.repositories.accounts.postgresql_player_session_repository import (
    PostgreSQLPlayerSessionRepository,
)


async def _count(database: Database, model: type[Base]) -> int:
    async with database.session() as session:
        return await session.scalar(select(func.count()).select_from(model))


def test_sql_unit_of_work_enforces_unique_pseudos_and_expires_sessions(sqlite_database: Database) -> None:
    async def scenario() -> None:
        account = PlayerAccount(id="a1", pseudo=Pseudo("Zoé"), password_hash="hash", created_at_ms=1)
        async with SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET) as uow:
            await uow.accounts.add(account)
            await uow.sessions.add(PlayerSession("t1", "a1", expires_at_ms=100))
            await uow.sessions.add(PlayerSession("t2", "a1", expires_at_ms=10_000))
            await uow.commit()

        async with SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET) as uow:
            assert await uow.accounts.find_by_pseudo(Pseudo("ZOÉ")) == account
            with pytest.raises(PseudoAlreadyTakenError):
                await uow.accounts.add(PlayerAccount(id="a2", pseudo=Pseudo("zoé"), password_hash="hash", created_at_ms=2))

        async with SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET) as uow:
            await uow.accounts.save_password_hash(account.with_password_hash("nouveau"))
            await uow.sessions.save_expiry(PlayerSession("t1", "a1", expires_at_ms=50).renewed(now_ms=0))
            await uow.commit()
            assert (await uow.accounts.get("a1")).password_hash == "nouveau"
            assert (await uow.sessions.get("t1")).expires_at_ms == SESSION_TTL_MS
            await uow.sessions.save_expiry(PlayerSession("t1", "a1", expires_at_ms=100))
            await uow.sessions.delete_expired(now_ms=100)
            await uow.sessions.delete("t2")
            await uow.commit()
            assert await uow.sessions.get("t1") is None and await uow.sessions.get("t2") is None

    asyncio.run(scenario())


def test_sql_registration_is_all_or_nothing(sqlite_database: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable(*_: object) -> None:
        raise RuntimeError("base indisponible")

    unit_of_work = lambda: SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET)  # noqa: E731
    clock = Clock()
    use_case = AccountCommandUseCase(unit_of_work, FakeHasher(), clock=clock)
    monkeypatch.setattr(PostgreSQLPlayerSessionRepository, "add", unavailable)
    with pytest.raises(RuntimeError):
        asyncio.run(use_case.register(make_credentials(), IP))
    assert asyncio.run(_count(sqlite_database, PlayerAccountModel)) == 0

    monkeypatch.undo()
    signed_in = asyncio.run(use_case.register(make_credentials(), IP))
    assert asyncio.run(AccountQueryUseCase(unit_of_work, clock=clock).current(signed_in.token)).account.pseudo == "Lucas"


def test_sql_attempt_counter_upserts_atomically_and_purges(sqlite_database: Database) -> None:
    async def scenario() -> None:
        async with SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET) as uow:
            assert await uow.attempts.hit("ip", IP, 1_000, 500) == AttemptWindow(1, 1_500)
            assert await uow.attempts.hit("ip", IP, 1_200, 500) == AttemptWindow(2, 1_500)
            assert await uow.attempts.hit("ip", IP, 1_600, 500) == AttemptWindow(1, 2_100)  # fenêtre expirée : on repart de 1
            await uow.attempts.hit("ip", "198.51.100.1", 0, 500)
            await uow.commit()

        async with sqlite_database.session() as session:
            keys = (await session.scalars(select(AuthAttemptModel.key))).all()
        plain_hash = hashlib.sha256(f"ip:{IP}".encode()).hexdigest()
        assert len(keys) == 2 and all(len(key) == 64 and IP not in key for key in keys)
        assert plain_hash not in keys  # HMAC : une table SHA-256 de toutes les adresses IPv4 ne retrouve rien

        async with SqlAccountUnitOfWork(sqlite_database, b"autre-secret-apres-rotation-0123456789") as uow:
            assert await uow.attempts.hit("ip", IP, 1_700, 500) == AttemptWindow(1, 2_200)  # rotation : on repart de zéro
            await uow.attempts.purge(started_before_ms=1_000)
            await uow.attempts.reset("ip", IP)
            await uow.commit()
        assert await _count(sqlite_database, AuthAttemptModel) == 1

    asyncio.run(scenario())
