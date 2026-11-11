from __future__ import annotations

import asyncio

import pytest
from account_support import (
    IP,
    InMemoryAccountUnitOfWork,
    build_accounts,
    make_credentials,
)

from application.accounts.account_maintenance import AccountMaintenance
from domain.accounts.constants.account_sessions import SESSION_TTL_MS
from exceptions import (
    NotAuthenticatedError,
)
from interface.workers.account_janitor import AccountJanitor


def test_the_janitor_purges_expired_sessions_and_stale_counters() -> None:
    commands, queries, store, clock = build_accounts()
    signed_in = asyncio.run(commands.register(make_credentials(), IP))
    clock.now += SESSION_TTL_MS

    maintenance = AccountMaintenance(lambda: InMemoryAccountUnitOfWork(store), clock=clock)
    asyncio.run(AccountJanitor(maintenance).run_once())
    assert store.sessions == {} and store.attempts == {}
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(queries.current(signed_in.token))
