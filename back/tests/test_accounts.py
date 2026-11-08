from __future__ import annotations

import asyncio
import hashlib
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import Optional, Self

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select

from application.accounts.account_commands import CredentialsCommand
from application.accounts.account_maintenance import AccountMaintenance
from application.accounts.account_unit_of_work import AccountUnitOfWork
from application.accounts.account_usecase import AccountUseCase, hash_session_token
from application.accounts.attempt_counter import AttemptCounter, AttemptWindow
from application.accounts.attempt_limit import AttemptLimit, enforce
from domain.accounts.models.password_policy import check_password, normalize_password
from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.player_session import (
    SESSION_RENEW_AFTER_MS,
    SESSION_TTL_MS,
    PlayerSession,
)
from domain.accounts.models.pseudo import Pseudo, check_pseudo_is_not_reserved
from domain.accounts.repositories.player_account_repository import (
    PlayerAccountRepository,
)
from domain.accounts.repositories.player_session_repository import (
    PlayerSessionRepository,
)
from domain.accounts.services.password_hasher import PasswordHasher
from exceptions import (
    InvalidAccountError,
    InvalidCredentialsError,
    NotAuthenticatedError,
    PseudoAlreadyTakenError,
    TooManyAttemptsError,
)
from infrastructure.config import Settings
from infrastructure.database.database import Base, Database
from infrastructure.database.models import AuthAttemptModel, PlayerAccountModel
from infrastructure.repositories.account_unit_of_work import SqlAccountUnitOfWork
from infrastructure.repositories.postgresql_player_session_repository import (
    PostgreSQLPlayerSessionRepository,
)
from infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from interface.api import accounts as accounts_api
from interface.dependencies.container import account_usecase
from interface.workers.account_janitor import AccountJanitor

BACK_DIR = Path(__file__).resolve().parents[1]
ATTEMPT_SECRET = b"secret-de-test-des-compteurs-0123456789"
PASSWORD = "Tartiflette au four 74"
IP = "203.0.113.7"


# --- Doubles en mémoire : une « base » et une unité de travail qui travaille sur une copie ---


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


def _use_case(
    hasher: Optional[FakeHasher] = None, *, store: Optional[AccountStore] = None, clock: Optional[Clock] = None, broken_sessions: bool = False
) -> tuple[AccountUseCase, AccountStore, Clock]:
    store, clock = store or AccountStore(), clock or Clock()
    use_case = AccountUseCase(lambda: InMemoryAccountUnitOfWork(store, broken_sessions=broken_sessions), hasher or FakeHasher(), clock=clock)
    return use_case, store, clock


def _credentials(pseudo: str = "Lucas", password: str = PASSWORD) -> CredentialsCommand:
    return CredentialsCommand(pseudo=pseudo, password=password)


# --- Règles du domaine ---


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


# --- Cas d'usage ---


def test_registering_opens_a_session_and_never_stores_the_password() -> None:
    use_case, store, _ = _use_case()
    signed_in = asyncio.run(use_case.register(_credentials(), IP))

    (account,) = store.accounts.values()
    assert account.pseudo.value == "Lucas" and PASSWORD not in account.password_hash.split("$", 1)[0]
    assert list(store.sessions) == [hash_session_token(signed_in.token)]  # seule l'empreinte du jeton est gardée
    assert asyncio.run(use_case.current(signed_in.token)).account.pseudo == "Lucas"


def test_an_account_never_exists_without_its_session() -> None:
    use_case, store, _ = _use_case(broken_sessions=True)

    with pytest.raises(RuntimeError):
        asyncio.run(use_case.register(_credentials(), IP))
    assert store.accounts == {} and store.sessions == {}  # tout ou rien : le pseudo reste libre


def test_a_pseudo_cannot_be_taken_twice_whatever_its_case() -> None:
    use_case, *_ = _use_case()
    asyncio.run(use_case.register(_credentials("Lucas"), IP))

    with pytest.raises(PseudoAlreadyTakenError):
        asyncio.run(use_case.register(_credentials("LUCAS"), "198.51.100.1"))


def test_login_with_the_right_password_works_whatever_the_pseudo_case() -> None:
    use_case, *_ = _use_case()
    asyncio.run(use_case.register(_credentials(), IP))

    assert asyncio.run(use_case.login(_credentials("lucas"), IP)).account.pseudo == "Lucas"


def test_a_wrong_password_and_an_unknown_pseudo_are_indistinguishable() -> None:
    hasher = FakeHasher()
    use_case, *_ = _use_case(hasher)
    asyncio.run(use_case.register(_credentials(), IP))

    messages = []
    for credentials in (_credentials(password="mauvais mot de passe"), _credentials(pseudo="Inconnu"), _credentials(pseudo="?!")):
        with pytest.raises(InvalidCredentialsError) as error:
            asyncio.run(use_case.login(credentials, IP))
        messages.append(error.value.message)
    assert len(set(messages)) == 1
    assert hasher.verifications == 3  # un pseudo inconnu coûte un hachage aussi : le temps de réponse ne trahit rien


def test_repeated_failures_lock_the_pseudo_for_a_while() -> None:
    use_case, _, clock = _use_case()
    asyncio.run(use_case.register(_credentials(), IP))
    for attempt in range(5):
        with pytest.raises(InvalidCredentialsError):
            asyncio.run(use_case.login(_credentials(password=f"essai {attempt} raté"), f"198.51.100.{attempt}"))

    with pytest.raises(TooManyAttemptsError) as locked:
        asyncio.run(use_case.login(_credentials(), "198.51.100.99"))  # même le bon mot de passe attend
    assert 0 < locked.value.retry_after_seconds <= 15 * 60

    clock.now += 15 * 60_000
    assert asyncio.run(use_case.login(_credentials(), IP)).account.pseudo == "Lucas"


def test_attempt_counters_survive_a_restart() -> None:
    first_process, store, clock = _use_case()
    asyncio.run(first_process.register(_credentials(), IP))
    for attempt in range(5):
        with pytest.raises(InvalidCredentialsError):
            asyncio.run(first_process.login(_credentials(password=f"essai {attempt} raté"), IP))

    restarted, *_ = _use_case(store=store, clock=clock)  # nouveau processus, même base
    with pytest.raises(TooManyAttemptsError):
        asyncio.run(restarted.login(_credentials(), IP))


def test_one_address_cannot_create_accounts_in_bulk() -> None:
    use_case, *_ = _use_case()
    for index in range(10):
        asyncio.run(use_case.register(_credentials(f"Joueur{index}"), IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(use_case.register(_credentials("Joueur10"), IP))


def test_refused_signups_consume_the_signup_limit_too() -> None:
    use_case, store, _ = _use_case()
    asyncio.run(use_case.register(_credentials("Lucas"), "198.51.100.1"))
    for attempt in range(10):  # pseudos pris, réservés, mots de passe faibles : chaque essai compte dès sa réception
        with pytest.raises(InvalidAccountError):
            asyncio.run(use_case.register(_credentials(("LUCAS", "Admin", "Zoe")[attempt % 3], "motdepasse" if attempt % 3 == 2 else PASSWORD), IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(use_case.register(_credentials("Valide"), IP))
    assert [account.pseudo.value for account in store.accounts.values()] == ["Lucas"]


def test_one_address_is_slowed_down_after_thirty_attempts_of_any_kind() -> None:
    use_case, *_ = _use_case()
    for attempt in range(30):
        with pytest.raises(InvalidCredentialsError):
            asyncio.run(use_case.login(_credentials(f"Inconnu{attempt}"), IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(use_case.register(_credentials(), IP))


def test_logout_and_expiry_end_the_session() -> None:
    use_case, store, clock = _use_case()
    first = asyncio.run(use_case.register(_credentials(), IP))
    asyncio.run(use_case.logout(first.token))
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(first.token))

    second = asyncio.run(use_case.login(_credentials(), IP))
    clock.now += SESSION_TTL_MS
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(second.token))
    assert store.sessions == {}


def test_signing_in_again_replaces_the_previous_session_atomically() -> None:
    use_case, store, _ = _use_case()
    first = asyncio.run(use_case.register(_credentials(), IP))

    second = asyncio.run(use_case.login(_credentials(), IP, replacing_token=first.token))
    assert list(store.sessions) == [hash_session_token(second.token)]


@pytest.mark.parametrize("token", [None, "", "x" * 129, "jeton-inconnu"])
def test_missing_or_forged_tokens_are_not_authenticated(token: Optional[str]) -> None:
    use_case, *_ = _use_case()

    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(token))


def test_an_accented_password_works_whatever_the_keyboard_encoding() -> None:
    use_case, *_ = _use_case()
    asyncio.run(use_case.register(_credentials(password="café crème glacée"), IP))

    assert asyncio.run(use_case.login(_credentials(password="café crème glacée"), IP)).account.pseudo == "Lucas"


def test_signing_up_with_a_reserved_pseudo_is_refused() -> None:
    use_case, store, _ = _use_case()

    with pytest.raises(InvalidAccountError, match="réservé"):
        asyncio.run(use_case.register(_credentials("Admin"), IP))
    assert store.accounts == {}


def test_an_active_player_session_slides_instead_of_expiring() -> None:
    use_case, store, clock = _use_case()
    signed_in = asyncio.run(use_case.register(_credentials(), IP))

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
    use_case, store, _ = _use_case(hasher)
    asyncio.run(use_case.register(_credentials(), IP))
    hasher.outdated = False

    asyncio.run(use_case.login(_credentials(), IP))
    assert next(iter(store.accounts.values())).password_hash.startswith("fake-v2$")


def test_a_reservation_counts_and_reports_in_one_step() -> None:
    counter, limit = InMemoryAttempts(AccountStore()), AttemptLimit("test", limit=2, window_ms=1_000)
    first, second, third = (asyncio.run(limit.reserve(counter, "joueur", at)) for at in (0, 10, 20))

    enforce(20, first, second)
    with pytest.raises(TooManyAttemptsError) as blocked:
        enforce(20, first, third)
    assert blocked.value.retry_after_seconds == 1
    assert not asyncio.run(limit.reserve(counter, "joueur", 1_000)).exceeded  # nouvelle fenêtre


def test_the_janitor_purges_expired_sessions_and_stale_counters() -> None:
    use_case, store, clock = _use_case()
    signed_in = asyncio.run(use_case.register(_credentials(), IP))
    clock.now += SESSION_TTL_MS

    maintenance = AccountMaintenance(lambda: InMemoryAccountUnitOfWork(store), clock=clock)
    asyncio.run(AccountJanitor(maintenance).run_once())
    assert store.sessions == {} and store.attempts == {}
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(signed_in.token))


# --- Infrastructure ---


def test_argon2id_hashes_are_salted_and_verified() -> None:
    hasher = Argon2PasswordHasher()

    first, second = asyncio.run(hasher.hash(PASSWORD)), asyncio.run(hasher.hash(PASSWORD))
    assert first.startswith("$argon2id$") and first != second and PASSWORD not in first
    assert asyncio.run(hasher.verify(first, PASSWORD)) is True
    assert asyncio.run(hasher.verify(first, PASSWORD + " ")) is False
    assert asyncio.run(hasher.verify(None, PASSWORD)) is False
    assert asyncio.run(hasher.verify("pas-un-hash", PASSWORD)) is False
    assert hasher.needs_rehash(first) is False


@pytest.fixture
def sqlite_database() -> Iterator[Database]:
    with tempfile.TemporaryDirectory() as directory:
        database = Database(f"sqlite+aiosqlite:///{Path(directory) / 'accounts.db'}")
        asyncio.run(database.create_schema())
        yield database
        asyncio.run(database.dispose())


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

    use_case = AccountUseCase(lambda: SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET), FakeHasher(), clock=Clock())
    monkeypatch.setattr(PostgreSQLPlayerSessionRepository, "add", unavailable)
    with pytest.raises(RuntimeError):
        asyncio.run(use_case.register(_credentials(), IP))
    assert asyncio.run(_count(sqlite_database, PlayerAccountModel)) == 0

    monkeypatch.undo()
    signed_in = asyncio.run(use_case.register(_credentials(), IP))
    assert asyncio.run(use_case.current(signed_in.token)).account.pseudo == "Lucas"


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


def test_concurrent_logins_cannot_exceed_the_pseudo_limit(sqlite_database: Database) -> None:
    """Cinq connexions simultanées alors qu'il ne reste qu'un essai : une seule atteint Argon2."""
    hasher, clock = FakeHasher(), Clock()
    use_case = AccountUseCase(lambda: SqlAccountUnitOfWork(sqlite_database, ATTEMPT_SECRET), hasher, clock=clock)

    async def scenario() -> list[BaseException | object]:
        await use_case.register(_credentials(), IP)
        for attempt in range(4):
            with pytest.raises(InvalidCredentialsError):
                await use_case.login(_credentials(password=f"essai {attempt} raté"), f"198.51.100.{attempt}")
        hasher.verifications = 0
        return await asyncio.gather(
            *(use_case.login(_credentials(password="encore raté"), f"203.0.113.{index}") for index in range(5)),
            return_exceptions=True,
        )

    outcomes = asyncio.run(scenario())
    assert sorted(type(outcome).__name__ for outcome in outcomes) == ["InvalidCredentialsError"] + ["TooManyAttemptsError"] * 4
    assert hasher.verifications == 1


def test_migrations_build_exactly_the_schema_of_the_models() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "migrated.db"
        config = Config(str(BACK_DIR / "alembic.ini"))
        config.attributes.update(database_url=f"sqlite+aiosqlite:///{path}", configure_logging=False)
        command.upgrade(config, "head")

        engine = create_engine(f"sqlite:///{path}")
        with engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)
        engine.dispose()
        assert differences == []
        command.downgrade(config, "base")


# --- API ---


def _client(monkeypatch: pytest.MonkeyPatch, *, environment: str = "development", player_origins: str = "") -> TestClient:
    return _client_with_state(monkeypatch, environment=environment, player_origins=player_origins)[0]


def _client_with_state(
    monkeypatch: pytest.MonkeyPatch, *, environment: str = "development", player_origins: str = ""
) -> tuple[TestClient, AccountStore, Clock]:
    from main import create_app

    settings = Settings(
        _env_file=None,
        environment=environment,
        controller_token="controller-test-token",
        display_token="display-test-token",
        hardware_token="hardware-test-token",
        player_origins=player_origins,
        trusted_proxies="10.0.0.1",
        rate_limit_secret="r" * 64,
    )
    monkeypatch.setattr(accounts_api, "get_settings", lambda: settings)
    app = create_app(settings)
    use_case, store, clock = _use_case()
    app.dependency_overrides[account_usecase] = lambda: use_case
    # Un navigateur annonce son origine sur chaque écriture ; les tests qui la retirent le font explicitement.
    return TestClient(app, base_url="http://testserver", headers={"Origin": "http://testserver"}), store, clock


def test_register_sets_an_httponly_strict_cookie_and_returns_only_the_pseudo(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    response = client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD})

    assert response.status_code == 201 and response.json() == {"pseudo": "Lucas"}
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("gb_session=") and "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
    assert response.headers["cache-control"] == "no-store"

    assert client.get("/api/accounts/me").json() == {"pseudo": "Lucas"}
    assert client.post("/api/accounts/logout").status_code == 204
    assert client.get("/api/accounts/me").status_code == 401


def test_login_errors_are_generic_and_never_echo_the_password(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD})
    client.cookies.clear()

    wrong = client.post("/api/accounts/login", json={"pseudo": "Lucas", "password": "secret-faux-123"})
    assert wrong.status_code == 401 and wrong.json() == {"detail": "Pseudo ou mot de passe incorrect."}
    malformed = client.post("/api/accounts/login", json={"pseudo": "Lucas", "password": 12345678, "extra": "secret-faux-123"})
    assert malformed.status_code == 422 and "secret-faux-123" not in malformed.text and "12345678" not in malformed.text
    assert client.post("/api/accounts/login", json={"pseudo": "lucas", "password": PASSWORD}).json() == {"pseudo": "Lucas"}


def test_too_many_attempts_answer_429_with_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    for _ in range(5):
        client.post("/api/accounts/login", json={"pseudo": "Lucas", "password": "secret-faux-123"})

    response = client.post("/api/accounts/login", json={"pseudo": "Lucas", "password": "secret-faux-123"})
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0


def test_requests_from_another_site_are_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    body = {"pseudo": "Lucas", "password": PASSWORD}

    forged = client.post("/api/accounts/register", json=body, headers={"Origin": "https://pirate.example"})
    assert forged.status_code == 403 and "set-cookie" not in forged.headers
    assert client.post("/api/accounts/register", json=body, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.post("/api/accounts/register", json=body, headers={"Origin": "http://testserver"}).status_code == 201


def test_a_configured_player_origin_is_the_only_one_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, player_origins="https://jeu.exemple.fr")
    body = {"pseudo": "Lucas", "password": PASSWORD}

    # Même l'hôte de la requête ne suffit plus : derrière un proxy, seule l'origine déclarée fait foi.
    assert client.post("/api/accounts/register", json=body, headers={"Origin": "http://testserver"}).status_code == 403
    assert client.post("/api/accounts/register", json=body, headers={"Origin": "http://jeu.exemple.fr"}).status_code == 403
    assert client.post("/api/accounts/register", json=body, headers={"Origin": "https://jeu.exemple.fr"}).status_code == 201


def test_oversized_bodies_are_refused_even_when_streamed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    url = "/api/accounts/register"

    assert client.post(url, json={"pseudo": "Lucas", "password": "x" * 5_000}).status_code == 413
    streamed = (chunk for chunk in [b'{"pseudo": "Lucas", "password": "', b"x" * 4_000, b'"}'])  # sans Content-Length
    assert client.post(url, content=streamed, headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post(url, content=b"{}", headers={"Content-Length": "deux"}).status_code == 413


def test_signing_in_again_revokes_the_previous_session_of_this_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    client, store, _ = _client_with_state(monkeypatch)
    client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD})
    first_token = client.cookies["gb_session"]

    client.post("/api/accounts/login", json={"pseudo": "Lucas", "password": PASSWORD})
    assert client.cookies["gb_session"] != first_token
    assert list(store.sessions) == [hash_session_token(client.cookies["gb_session"])]


def test_me_refreshes_the_cookie_only_when_the_session_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, clock = _client_with_state(monkeypatch)
    client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD})

    assert "set-cookie" not in client.get("/api/accounts/me").headers
    clock.now += SESSION_RENEW_AFTER_MS + 1
    refreshed = client.get("/api/accounts/me")
    assert refreshed.json() == {"pseudo": "Lucas"} and f"Max-Age={SESSION_TTL_MS // 1000}" in refreshed.headers["set-cookie"]


def test_production_cookies_are_secure_and_host_only(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, environment="production", player_origins="http://testserver")
    cookie = client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD}).headers["set-cookie"]

    assert cookie.startswith("__Host-gb_session=") and "Secure" in cookie and "Domain" not in cookie


def test_rule_errors_name_the_field_to_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    register = "/api/accounts/register"
    client.post(register, json={"pseudo": "Lucas", "password": PASSWORD})
    client.cookies.clear()

    taken = client.post(register, json={"pseudo": "LUCAS", "password": PASSWORD})
    assert taken.status_code == 409 and taken.json() == {"detail": "Ce pseudo est déjà pris.", "field": "pseudo"}
    assert client.post(register, json={"pseudo": "Admin", "password": PASSWORD}).json()["field"] == "pseudo"
    weak = client.post(register, json={"pseudo": "Zoe", "password": "motdepasse"})
    assert weak.status_code == 400 and weak.json()["field"] == "password"
    assert "field" not in client.post("/api/accounts/login", json={"pseudo": "Lucas", "password": "faux-faux-faux"}).json()


def test_writes_must_announce_their_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    del client.headers["Origin"]
    body = {"pseudo": "Lucas", "password": PASSWORD}

    assert client.post("/api/accounts/register", json=body).status_code == 403  # ni Origin ni Referer
    assert client.post("/api/accounts/register", json=body, headers={"Origin": "null"}).status_code == 403
    assert client.post("/api/accounts/register", json=body, headers={"Referer": "https://pirate.example/page"}).status_code == 403
    assert client.post("/api/accounts/register", json=body, headers={"Referer": "http://testserver/"}).status_code == 201
    assert client.post("/api/accounts/logout").status_code == 403
    assert client.get("/api/accounts/me").json() == {"pseudo": "Lucas"}  # une lecture n'a pas besoin d'origine


def test_cors_never_lets_another_site_use_the_session_cookie(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    preflight = client.options(
        "/api/accounts/login",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )

    # Contrat de déploiement : app joueur et API sur la même origine. Même une origine CORS autorisée n'obtient pas les cookies.
    assert "access-control-allow-credentials" not in preflight.headers
