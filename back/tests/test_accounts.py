from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from application.accounts.account_commands import CredentialsCommand
from application.accounts.account_usecase import (
    AccountUseCase,
    hash_session_token,
)
from application.accounts.attempt_limiter import AttemptLimiter
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
from infrastructure.database.database import Database
from infrastructure.repositories.postgresql_player_account import (
    PostgreSQLPlayerAccountRepository,
    PostgreSQLPlayerSessionRepository,
)
from infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from interface.api import accounts as accounts_api
from interface.dependencies.container import account_usecase

PASSWORD = "Tartiflette au four 74"
IP = "203.0.113.7"


class InMemoryAccounts(PlayerAccountRepository):
    def __init__(self) -> None:
        self.by_id: dict[str, PlayerAccount] = {}

    async def get(self, account_id: str) -> Optional[PlayerAccount]:
        return self.by_id.get(account_id)

    async def find_by_pseudo(self, pseudo: Pseudo) -> Optional[PlayerAccount]:
        return next((account for account in self.by_id.values() if account.pseudo.key == pseudo.key), None)

    async def add(self, account: PlayerAccount) -> None:
        if await self.find_by_pseudo(account.pseudo):
            raise PseudoAlreadyTakenError("Ce pseudo est déjà pris.")
        self.by_id[account.id] = account

    async def save_password_hash(self, account: PlayerAccount) -> None:
        self.by_id[account.id] = account


class InMemorySessions(PlayerSessionRepository):
    def __init__(self) -> None:
        self.by_hash: dict[str, PlayerSession] = {}

    async def add(self, session: PlayerSession) -> None:
        self.by_hash[session.token_hash] = session

    async def get(self, token_hash: str) -> Optional[PlayerSession]:
        return self.by_hash.get(token_hash)

    async def delete(self, token_hash: str) -> None:
        self.by_hash.pop(token_hash, None)

    async def save_expiry(self, session: PlayerSession) -> None:
        self.by_hash[session.token_hash] = session

    async def delete_expired(self, now_ms: int) -> None:
        self.by_hash = {key: session for key, session in self.by_hash.items() if not session.is_expired(now_ms)}


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


def _use_case(hasher: Optional[FakeHasher] = None) -> tuple[AccountUseCase, InMemoryAccounts, InMemorySessions, Clock]:
    accounts, sessions, clock = InMemoryAccounts(), InMemorySessions(), Clock()
    return AccountUseCase(accounts, sessions, hasher or FakeHasher(), clock=clock), accounts, sessions, clock


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
    assert normalize_password("cafe\u0301 au lait") == normalize_password("caf\u00e9 au lait")


# --- Cas d'usage ---


def test_registering_opens_a_session_and_never_stores_the_password() -> None:
    use_case, accounts, sessions, _ = _use_case()
    signed_in = asyncio.run(use_case.register(_credentials(), IP))

    (account,) = accounts.by_id.values()
    assert account.pseudo.value == "Lucas" and PASSWORD not in account.password_hash.split("$", 1)[0]
    assert list(sessions.by_hash) == [hash_session_token(signed_in.token)]  # seule l'empreinte du jeton est gardée
    assert asyncio.run(use_case.current(signed_in.token)).account.pseudo == "Lucas"


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
    use_case, _, _, clock = _use_case()
    asyncio.run(use_case.register(_credentials(), IP))
    for attempt in range(5):
        with pytest.raises(InvalidCredentialsError):
            asyncio.run(use_case.login(_credentials(password=f"essai {attempt} raté"), f"198.51.100.{attempt}"))

    with pytest.raises(TooManyAttemptsError) as locked:
        asyncio.run(use_case.login(_credentials(), "198.51.100.99"))  # même le bon mot de passe attend
    assert 0 < locked.value.retry_after_seconds <= 15 * 60

    clock.now += 15 * 60_000
    assert asyncio.run(use_case.login(_credentials(), IP)).account.pseudo == "Lucas"


def test_one_address_cannot_create_accounts_in_bulk() -> None:
    use_case, *_ = _use_case()
    for index in range(5):
        asyncio.run(use_case.register(_credentials(f"Joueur{index}"), IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(use_case.register(_credentials("Joueur5"), IP))


def test_logout_and_expiry_end_the_session() -> None:
    use_case, _, sessions, clock = _use_case()
    first = asyncio.run(use_case.register(_credentials(), IP))
    asyncio.run(use_case.logout(first.token))
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(first.token))

    second = asyncio.run(use_case.login(_credentials(), IP))
    clock.now += SESSION_TTL_MS
    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(second.token))
    assert sessions.by_hash == {}


@pytest.mark.parametrize("token", [None, "", "x" * 129, "jeton-inconnu"])
def test_missing_or_forged_tokens_are_not_authenticated(token: Optional[str]) -> None:
    use_case, *_ = _use_case()

    with pytest.raises(NotAuthenticatedError):
        asyncio.run(use_case.current(token))


def test_an_accented_password_works_whatever_the_keyboard_encoding() -> None:
    use_case, *_ = _use_case()
    asyncio.run(use_case.register(_credentials(password="caf\u00e9 crème glacée"), IP))

    assert asyncio.run(use_case.login(_credentials(password="cafe\u0301 cre\u0300me glace\u0301e"), IP)).account.pseudo == "Lucas"


def test_signing_up_with_a_reserved_pseudo_is_refused() -> None:
    use_case, accounts, *_ = _use_case()

    with pytest.raises(InvalidAccountError, match="réservé"):
        asyncio.run(use_case.register(_credentials("Admin"), IP))
    assert accounts.by_id == {}


def test_an_active_player_session_slides_instead_of_expiring() -> None:
    use_case, _, sessions, clock = _use_case()
    signed_in = asyncio.run(use_case.register(_credentials(), IP))

    clock.now += SESSION_RENEW_AFTER_MS - 60_000
    assert asyncio.run(use_case.current(signed_in.token)).renewed_until_ms is None  # pas d'écriture à chaque visite
    clock.now += 2 * 60_000
    renewed = asyncio.run(use_case.current(signed_in.token))
    assert renewed.renewed_until_ms == clock.now + SESSION_TTL_MS
    assert sessions.by_hash[hash_session_token(signed_in.token)].expires_at_ms == renewed.renewed_until_ms

    clock.now += SESSION_TTL_MS - 1
    assert asyncio.run(use_case.current(signed_in.token)).account.pseudo == "Lucas"


def test_an_outdated_hash_is_upgraded_at_the_next_login() -> None:
    hasher = FakeHasher(outdated=True)
    use_case, accounts, *_ = _use_case(hasher)
    asyncio.run(use_case.register(_credentials(), IP))
    hasher.outdated = False

    asyncio.run(use_case.login(_credentials(), IP))
    assert next(iter(accounts.by_id.values())).password_hash.startswith("fake-v2$")


def test_the_attempt_limiter_keeps_a_bounded_number_of_keys() -> None:
    limiter = AttemptLimiter(limit=1, window_ms=1_000, max_keys=3)
    for index in range(10):
        limiter.record(f"ip-{index}", 0)

    limiter.check("ip-0", 1)  # évincée : la mémoire ne grossit pas
    with pytest.raises(TooManyAttemptsError):
        limiter.check("ip-9", 1)


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


def test_sql_repositories_enforce_unique_pseudos_and_expire_sessions() -> None:
    async def scenario(database: Database) -> None:
        await database.create_schema()
        accounts, sessions = PostgreSQLPlayerAccountRepository(database), PostgreSQLPlayerSessionRepository(database)
        account = PlayerAccount(id="a1", pseudo=Pseudo("Zoé"), password_hash="hash", created_at_ms=1)
        await accounts.add(account)
        assert await accounts.find_by_pseudo(Pseudo("ZOÉ")) == account
        with pytest.raises(PseudoAlreadyTakenError):
            await accounts.add(PlayerAccount(id="a2", pseudo=Pseudo("zoé"), password_hash="hash", created_at_ms=2))

        await accounts.save_password_hash(account.with_password_hash("nouveau"))
        assert (await accounts.get("a1")).password_hash == "nouveau"

        await sessions.add(PlayerSession("t1", "a1", expires_at_ms=100))
        await sessions.add(PlayerSession("t2", "a1", expires_at_ms=10_000))
        await sessions.save_expiry(PlayerSession("t1", "a1", expires_at_ms=50).renewed(now_ms=0))
        assert (await sessions.get("t1")).expires_at_ms == SESSION_TTL_MS
        await sessions.save_expiry(PlayerSession("t1", "a1", expires_at_ms=100))
        await sessions.delete_expired(now_ms=100)
        assert await sessions.get("t1") is None and await sessions.get("t2") is not None
        await sessions.delete("t2")
        assert await sessions.get("t2") is None
        await database.dispose()

    with tempfile.TemporaryDirectory() as directory:
        asyncio.run(scenario(Database(f"sqlite+aiosqlite:///{Path(directory) / 'accounts.db'}")))


# --- API ---


def _client(monkeypatch: pytest.MonkeyPatch, *, environment: str = "development") -> TestClient:
    return _client_with_state(monkeypatch, environment=environment)[0]


def _client_with_state(
    monkeypatch: pytest.MonkeyPatch, *, environment: str = "development"
) -> tuple[TestClient, InMemorySessions, Clock]:
    from main import create_app

    settings = Settings(
        _env_file=None,
        environment=environment,
        controller_token="controller-test-token",
        display_token="display-test-token",
        hardware_token="hardware-test-token",
    )
    monkeypatch.setattr(accounts_api, "get_settings", lambda: settings)
    app = create_app(settings)
    use_case, _, sessions, clock = _use_case()
    app.dependency_overrides[account_usecase] = lambda: use_case
    return TestClient(app, base_url="http://testserver"), sessions, clock


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

    forged = client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD}, headers={"Origin": "https://pirate.example"})
    assert forged.status_code == 403 and "set-cookie" not in forged.headers
    same_site = client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD}, headers={"Origin": "http://testserver"})
    assert same_site.status_code == 201


def test_oversized_bodies_are_refused_even_when_streamed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    url = "/api/accounts/register"

    assert client.post(url, json={"pseudo": "Lucas", "password": "x" * 5_000}).status_code == 413
    streamed = (chunk for chunk in [b'{"pseudo": "Lucas", "password": "', b"x" * 4_000, b'"}'])  # sans Content-Length
    assert client.post(url, content=streamed, headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post(url, content=b"{}", headers={"Content-Length": "deux"}).status_code == 413


def test_signing_in_again_revokes_the_previous_session_of_this_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    client, sessions, _ = _client_with_state(monkeypatch)
    client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD})
    first_token = client.cookies["gb_session"]

    client.post("/api/accounts/login", json={"pseudo": "Lucas", "password": PASSWORD})
    assert client.cookies["gb_session"] != first_token
    assert list(sessions.by_hash) == [hash_session_token(client.cookies["gb_session"])]


def test_me_refreshes_the_cookie_only_when_the_session_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, clock = _client_with_state(monkeypatch)
    client.post("/api/accounts/register", json={"pseudo": "Lucas", "password": PASSWORD})

    assert "set-cookie" not in client.get("/api/accounts/me").headers
    clock.now += SESSION_RENEW_AFTER_MS + 1
    refreshed = client.get("/api/accounts/me")
    assert refreshed.json() == {"pseudo": "Lucas"} and f"Max-Age={SESSION_TTL_MS // 1000}" in refreshed.headers["set-cookie"]


def test_production_cookies_are_secure_and_host_only(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch, environment="production")
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
