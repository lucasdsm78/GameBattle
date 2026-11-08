from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType
from typing import Optional, Self

from application.accounts.account_commands import CredentialsCommand
from application.accounts.account_unit_of_work import AccountUnitOfWork
from application.accounts.account_usecase import AccountUseCase
from application.accounts.attempt_counter import AttemptCounter, AttemptWindow
from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.player_session import (
    PlayerSession,
)
from domain.accounts.models.pseudo import Pseudo
from domain.accounts.repositories.player_account_repository import (
    PlayerAccountRepository,
)
from domain.accounts.repositories.player_session_repository import (
    PlayerSessionRepository,
)
from domain.accounts.services.password_hasher import PasswordHasher
from exceptions import (
    PseudoAlreadyTakenError,
)

ATTEMPT_SECRET = b"secret-de-test-des-compteurs-0123456789"


PASSWORD = "Tartiflette au four 74"


IP = "203.0.113.7"


@dataclass
class AccountStore:
    accounts: dict[str, PlayerAccount] = field(default_factory=dict)
    sessions: dict[str, PlayerSession] = field(default_factory=dict)
    attempts: dict[str, tuple[int, int]] = field(default_factory=dict)  # clé -> (début de fenêtre, essais)

    def copy(self) -> AccountStore:
        return AccountStore(dict(self.accounts), dict(self.sessions), dict(self.attempts))


class InMemoryAccounts(PlayerAccountRepository):
    def __init__(self, data: AccountStore) -> None:
        self._data = data

    async def get(self, account_id: str) -> Optional[PlayerAccount]:
        return self._data.accounts.get(account_id)

    async def find_by_pseudo(self, pseudo: Pseudo) -> Optional[PlayerAccount]:
        return next((account for account in self._data.accounts.values() if account.pseudo.key == pseudo.key), None)

    async def add(self, account: PlayerAccount) -> None:
        if await self.find_by_pseudo(account.pseudo):
            raise PseudoAlreadyTakenError("Ce pseudo est déjà pris.")
        self._data.accounts[account.id] = account

    async def save_password_hash(self, account: PlayerAccount) -> None:
        self._data.accounts[account.id] = account


class InMemorySessions(PlayerSessionRepository):
    def __init__(self, data: AccountStore, *, broken: bool = False) -> None:
        self._data = data
        self._broken = broken

    async def add(self, session: PlayerSession) -> None:
        if self._broken:
            raise RuntimeError("base indisponible")
        self._data.sessions[session.token_hash] = session

    async def get(self, token_hash: str) -> Optional[PlayerSession]:
        return self._data.sessions.get(token_hash)

    async def save_expiry(self, session: PlayerSession) -> None:
        self._data.sessions[session.token_hash] = session

    async def delete(self, token_hash: str) -> None:
        self._data.sessions.pop(token_hash, None)

    async def delete_expired(self, now_ms: int) -> None:
        self._data.sessions = {key: session for key, session in self._data.sessions.items() if not session.is_expired(now_ms)}


class InMemoryAttempts(AttemptCounter):
    def __init__(self, data: AccountStore) -> None:
        self._data = data

    async def hit(self, scope: str, subject: str, now_ms: int, window_ms: int) -> AttemptWindow:
        start, count = self._data.attempts.get(f"{scope}:{subject}", (now_ms, 0))
        if now_ms >= start + window_ms:
            start, count = now_ms, 0
        self._data.attempts[f"{scope}:{subject}"] = (start, count + 1)
        return AttemptWindow(count + 1, start + window_ms)

    async def reset(self, scope: str, subject: str) -> None:
        self._data.attempts.pop(f"{scope}:{subject}", None)

    async def purge(self, started_before_ms: int) -> None:
        self._data.attempts = {key: value for key, value in self._data.attempts.items() if value[0] >= started_before_ms}


class InMemoryAccountUnitOfWork(AccountUnitOfWork):
    """Travaille sur une copie de la « base » : seul `commit()` publie, comme une vraie transaction."""

    def __init__(self, store: AccountStore, *, broken_sessions: bool = False) -> None:
        self._store = store
        self._broken_sessions = broken_sessions

    async def __aenter__(self) -> Self:
        self._work = self._store.copy()
        self.accounts = InMemoryAccounts(self._work)
        self.sessions = InMemorySessions(self._work, broken=self._broken_sessions)
        self.attempts = InMemoryAttempts(self._work)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        return None

    async def commit(self) -> None:
        committed = self._work.copy()
        self._store.accounts, self._store.sessions, self._store.attempts = committed.accounts, committed.sessions, committed.attempts


class FakeHasher(PasswordHasher):
    """Rapide et déterministe ; compte les vérifications pour prouver qu'un pseudo inconnu en coûte une aussi."""

    def __init__(self, outdated: bool = False) -> None:
        self.outdated = outdated
        self.verifications = 0

    async def hash(self, password: str) -> str:
        return f"fake-v{1 if self.outdated else 2}${password}"

    async def verify(self, password_hash: Optional[str], password: str) -> bool:
        self.verifications += 1
        return password_hash is not None and password_hash.split("$", 1)[1] == password

    def needs_rehash(self, password_hash: str) -> bool:
        return not password_hash.startswith("fake-v2$")


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000

    def __call__(self) -> int:
        return self.now


def build_use_case(
    hasher: Optional[FakeHasher] = None, *, store: Optional[AccountStore] = None, clock: Optional[Clock] = None, broken_sessions: bool = False
) -> tuple[AccountUseCase, AccountStore, Clock]:
    store, clock = store or AccountStore(), clock or Clock()
    use_case = AccountUseCase(lambda: InMemoryAccountUnitOfWork(store, broken_sessions=broken_sessions), hasher or FakeHasher(), clock=clock)
    return use_case, store, clock


def make_credentials(pseudo: str = "Lucas", password: str = PASSWORD) -> CredentialsCommand:
    return CredentialsCommand(pseudo=pseudo, password=password)
