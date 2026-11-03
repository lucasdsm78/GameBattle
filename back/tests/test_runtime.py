from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import pytest

from infrastructure.database.single_instance_lock import (
    API_INSTANCE_LOCK_ID,
    AnotherInstanceRunningError,
    SingleInstanceLock,
)
from infrastructure.runtime.periodic_task import PeriodicTask
from interface import client_address as client_address_module
from interface.client_address import resolve_client_address


class FakeConnection:
    def __init__(self, server: FakePostgres) -> None:
        self._server = server
        self.closed = False

    async def scalar(self, statement: Any, parameters: dict[str, int]) -> bool:
        assert "pg_try_advisory_lock" in str(statement) and parameters == {"id": API_INSTANCE_LOCK_ID}
        if self._server.holder is not None:
            return False
        self._server.holder = self
        return True

    async def execute(self, statement: Any, parameters: dict[str, int]) -> None:
        assert "pg_advisory_unlock" in str(statement) and self._server.holder is self
        self._server.holder = None

    async def commit(self) -> None:
        return None

    async def close(self) -> None:
        self.closed = True
        if self._server.holder is self:  # comme PostgreSQL : la fin de session libère le verrou
            self._server.holder = None


class FakePostgres:
    dialect_name = "postgresql"

    def __init__(self) -> None:
        self.holder: FakeConnection | None = None
        self.connections: list[FakeConnection] = []

    async def connect(self) -> FakeConnection:
        self.connections.append(FakeConnection(self))
        return self.connections[-1]


def test_a_second_api_instance_refuses_to_start() -> None:
    server = FakePostgres()
    first, second = SingleInstanceLock(server), SingleInstanceLock(server)  # type: ignore[arg-type]

    asyncio.run(first.acquire())
    with pytest.raises(AnotherInstanceRunningError, match="un seul processus"):
        asyncio.run(second.acquire())
    assert server.connections[1].closed  # la connexion de l'instance refusée ne traîne pas

    asyncio.run(first.release())
    asyncio.run(second.acquire())  # une fois la première arrêtée, une nouvelle instance peut démarrer
    assert server.holder is server.connections[2]


def test_the_lock_is_not_needed_without_postgresql() -> None:
    class Sqlite:
        dialect_name = "sqlite"

    asyncio.run(SingleInstanceLock(Sqlite()).acquire())  # type: ignore[arg-type]


class FlakyTask(PeriodicTask):
    name = "test.flaky"

    def __init__(self, failures: int) -> None:
        super().__init__(interval_seconds=600)
        self.remaining_failures = failures

    async def run_once(self) -> None:
        if self.remaining_failures:
            self.remaining_failures -= 1
            raise RuntimeError("base indisponible")


def test_a_failing_task_retries_quickly_with_backoff_then_recovers(caplog: pytest.LogCaptureFixture) -> None:
    task = FlakyTask(failures=12)
    delays = []
    with caplog.at_level(logging.INFO):
        for _ in range(13):
            asyncio.run(task.tick())
            delays.append(task.next_delay_seconds())

    assert delays[:5] == [1, 2, 4, 8, 16] and max(delays[:12]) == 600  # plafonné à l'intervalle normal
    assert delays[12] == 600 and task.consecutive_failures == 0  # rétablie : retour au rythme normal
    failure = next(record for record in caplog.records if record.message.startswith("test.flaky.failed"))
    assert failure.consecutive_failures == 1 and failure.message == "test.flaky.failed consecutive_failures=1 retry_in=1s"
    assert any(record.message == "test.flaky.recovered after_failures=12" for record in caplog.records)


def test_forwarding_from_an_unknown_peer_is_reported_once(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client_address_module, "_reported_peers", set())
    proxies = [ipaddress.ip_network("172.30.0.10/32")]
    with caplog.at_level(logging.WARNING):
        for _ in range(3):
            assert resolve_client_address("172.30.0.99", "198.51.100.1", proxies) == "172.30.0.99"
        resolve_client_address("203.0.113.7", None, proxies)  # sans en-tête : rien d'anormal

    reports = [record for record in caplog.records if record.message.startswith("client_address.untrusted_forwarded_for")]
    assert [record.message for record in reports] == ["client_address.untrusted_forwarded_for peer=172.30.0.99"]
