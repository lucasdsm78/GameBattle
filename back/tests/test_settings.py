from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from infrastructure.config import Settings

DEPLOYED = {
    "controller_token": "controller-token-secret",
    "display_token": "display-token-secret",
    "hardware_token": "hardware-token-secret",
    "player_origins": "https://jeu.exemple.fr/",
    "trusted_proxies": "172.30.0.10",
    "rate_limit_secret": "r" * 64,
}


def _deployed(environment: str = "production", **overrides: Any) -> Settings:
    return Settings(_env_file=None, environment=environment, **{**DEPLOYED, **overrides})


def test_production_rejects_default_security_tokens() -> None:
    with pytest.raises(ValidationError, match="controller_token"):
        _deployed(controller_token="change-me-controller", display_token="change-me-display", hardware_token="change-me-hardware")


def test_production_accepts_custom_security_tokens() -> None:
    settings = _deployed()

    assert settings.is_production is True and settings.is_deployed is True
    assert settings.controller_token == "controller-token-secret"
    assert settings.player_origins_set == {"https://jeu.exemple.fr"}
    assert settings.creates_schema_on_startup is False  # déployé, seules les migrations font évoluer le schéma


@pytest.mark.parametrize(
    ("field", "message"),
    [("player_origins", "player_origins"), ("trusted_proxies", "trusted_proxies"), ("rate_limit_secret", "32 caractères")],
)
def test_a_deployment_requires_every_security_setting(field: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _deployed(**{field: ""})


@pytest.mark.parametrize("environment", ["staging", "recette", "preprod", "prodution"])
def test_any_non_local_environment_is_held_to_production_rules(environment: str) -> None:
    # Une faute de frappe (« prodution ») durcit la configuration au lieu de l'affaiblir.
    with pytest.raises(ValidationError, match=f"« {environment} »"):
        _deployed(environment, rate_limit_secret="")
    assert _deployed(environment).is_deployed is True


@pytest.mark.parametrize(("secret", "message"), [("trop-court", "32 caractères"), ("controller-token-secret" * 2, "dédié")])
def test_a_deployment_requires_a_dedicated_rate_limit_secret(secret: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _deployed(controller_token="controller-token-secret" * 2, rate_limit_secret=secret)


@pytest.mark.parametrize("secret", [f" {'a' * 64}", f"{'a' * 64}\n", f"{'a' * 32} {'a' * 32}"])
def test_a_rate_limit_secret_with_whitespace_is_refused_everywhere(secret: str) -> None:
    with pytest.raises(ValidationError, match="aucun espace"):
        Settings(_env_file=None, rate_limit_secret=secret)


@pytest.mark.parametrize("environment", ["development", "dev", "local", "test"])
def test_local_environments_get_a_random_rate_limit_secret(environment: str) -> None:
    first, second = Settings(_env_file=None, environment=environment), Settings(_env_file=None, environment=environment)

    assert first.is_deployed is False and first.creates_schema_on_startup is True
    assert len(first.rate_limit_secret) == 64 and first.rate_limit_secret != second.rate_limit_secret
