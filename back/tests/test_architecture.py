from __future__ import annotations

import ast
from pathlib import Path
from typing import get_args

import pytest

from application.game_night.game_night_commands import GameKey
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from domain.game_night.models.session import GameSession
from domain.game_night.models.settings import SUPPORTED_GAME_KEYS
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


GAME_MODULES = ("blindtest", "culture", "stopchrono", "bombe", "memory", "seven_differences", "auction", "forbidden_word")


def _domain_dependencies(module: str) -> set[str]:
    return {
        imported.split(".")[1]
        for path in (BACK_DIR / "domain" / module).rglob("*.py")
        for imported in _imported_modules(path)
        if imported.startswith("domain.") and imported.count(".") >= 1
    }


@pytest.mark.parametrize("game", GAME_MODULES)
def test_a_game_only_depends_on_the_shared_kernel(game: str) -> None:
    assert _domain_dependencies(game) <= {game, "shared"}


def test_the_shared_kernel_depends_on_no_other_domain_module() -> None:
    assert _domain_dependencies("shared") <= {"shared"}


def test_every_domain_module_follows_the_same_layout() -> None:
    expected = {"game_night", "shared", *GAME_MODULES}
    modules = {path.name for path in (BACK_DIR / "domain").iterdir() if path.is_dir() and path.name != "__pycache__"}

    assert modules == expected
    assert all((BACK_DIR / "domain" / module / "models").is_dir() for module in expected)
