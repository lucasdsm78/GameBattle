from __future__ import annotations

import pytest
from account_support import (
    PASSWORD,
    AccountStore,
    Clock,
    build_use_case,
)
from fastapi.testclient import TestClient

from application.accounts.account_usecase import hash_session_token
from domain.accounts.models.player_session import (
    SESSION_RENEW_AFTER_MS,
    SESSION_TTL_MS,
)
from infrastructure.config import Settings
from interface.api import accounts as accounts_api
from interface.dependencies.container import account_usecase


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
    use_case, store, clock = build_use_case()
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
