from __future__ import annotations

import ast
from pathlib import Path
from typing import get_args

import pytest

from application.game_night.game_night_commands import GameKey
from domain.models.games import GAME_STATE_TYPES
from domain.models.session import GameSession
from domain.models.settings import SUPPORTED_GAME_KEYS
from interface.realtime.routes import ROUTES


def test_every_game_is_registered_consistently_across_layers() -> None:
    session_fields = set(GameSession.__dataclass_fields__)

    assert set(GAME_STATE_TYPES) == SUPPORTED_GAME_KEYS == set(get_args(GameKey))
    assert set(GAME_STATE_TYPES) <= session_fields


def test_websocket_events_are_unique() -> None:
    names = [route.event for route in ROUTES]

    assert len(names) == len(set(names))


def test_display_can_only_trigger_buzzers_timers_and_spotify_token() -> None:
    display_commands = {route.event for route in ROUTES if "display" in route.roles}

    assert display_commands == {
        "blindtest.buzzer",
        "spotify.user-token",
        "stopchrono.start",
        "stopchrono.stop",
        "culture.buzzer",
        "bombe.buzzer",
        "bombe.begin-after-roll",
        "bombe.explode",
        "seven-differences.open",
        "seven-differences.buzzer",
        "auction.buzzer",
    }


BACK_DIR = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = {
    "domain": ("application", "infrastructure", "interface", "fastapi", "pydantic", "sqlalchemy", "httpx"),
    "application": ("infrastructure", "interface", "fastapi", "sqlalchemy", "httpx"),
    "infrastructure": ("interface", "fastapi"),
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_layers_only_depend_inwards(layer: str) -> None:
    violations = [
        f"{path.relative_to(BACK_DIR)} -> {module}"
        for path in (BACK_DIR / layer).rglob("*.py")
        for module in _imported_modules(path)
        if module.split(".")[0] in FORBIDDEN_IMPORTS[layer]
    ]

    assert violations == []
