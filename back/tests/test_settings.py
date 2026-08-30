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
    )

    assert settings.is_production is True
    assert settings.controller_token == "controller-token-secret"


