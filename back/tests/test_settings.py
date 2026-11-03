from __future__ import annotations

import pytest
from pydantic import ValidationError

from infrastructure.config import Settings


def test_production_rejects_default_security_tokens() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            controller_token="change-me-controller",
            display_token="change-me-display",
            hardware_token="change-me-hardware",
        )


def test_production_accepts_custom_security_tokens() -> None:
    settings = Settings(
        environment="production",
        controller_token="controller-token-secret",
        display_token="display-token-secret",
        hardware_token="hardware-token-secret",
        player_origins="https://jeu.exemple.fr/",
        rate_limit_secret="r" * 64,
    )

    assert settings.is_production is True
    assert settings.controller_token == "controller-token-secret"
    assert settings.player_origins_set == {"https://jeu.exemple.fr"}
    assert settings.creates_schema_on_startup is False  # en production, seules les migrations font évoluer le schéma


def test_production_requires_the_player_app_origin() -> None:
    with pytest.raises(ValidationError, match="player_origins"):
        Settings(
            environment="production",
            controller_token="controller-token-secret",
            display_token="display-token-secret",
            hardware_token="hardware-token-secret",
            player_origins="",
            rate_limit_secret="r" * 64,
        )


@pytest.mark.parametrize(("secret", "message"), [("", "32 caractères"), ("trop-court", "32 caractères"), ("controller-token-secret" * 2, "dédié")])
def test_production_requires_a_dedicated_rate_limit_secret(secret: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(
            environment="production",
            controller_token="controller-token-secret" * 2,
            display_token="display-token-secret",
            hardware_token="hardware-token-secret",
            player_origins="https://jeu.exemple.fr",
            rate_limit_secret=secret,
        )


def test_development_gets_a_random_rate_limit_secret() -> None:
    first, second = Settings(_env_file=None), Settings(_env_file=None)

    assert len(first.rate_limit_secret) == 64 and first.rate_limit_secret != second.rate_limit_secret


