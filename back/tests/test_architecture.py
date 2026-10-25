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
        "vanishing-word.buzzer",
        "flash-calc.buzzer",
        "right-flag.buzzer",
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


GAME_MODULES = (
    "blindtest", "culture", "stopchrono", "bombe", "memory", "seven_differences", "auction", "forbidden_word", "vanishing_word",
    "flash_calc", "right_flag",
)


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


def test_every_game_has_its_state_and_actions_composed_into_the_aggregate() -> None:
    from domain.game_night.models.game_config import GameConfig
    from domain.shared.models.game_actions import GameActions

    for game in GAME_MODULES:
        models = BACK_DIR / "domain" / game / "models"
        assert (models / f"{game}_state.py").is_file(), game
        assert (models / f"{game}_actions.py").is_file(), game

    composed = {
        base.__module__.split(".")[1]
        for base in GameConfig.__mro__
        if issubclass(base, GameActions) and base not in (GameActions, GameConfig)
    }
    assert composed == set(GAME_MODULES)


PRESENTATION_MEMBERS = {"to_dict", "to_payload", "client_views", "shared_view", "display_view", "payload_extras", "private_fields"}


def test_the_domain_knows_nothing_about_client_views() -> None:
    from domain.game_night.models.game_config import GameConfig

    for model in (GameConfig, GameSession, *GAME_STATE_TYPES.values()):
        assert PRESENTATION_MEMBERS.isdisjoint(dir(model)), model.__name__


def test_every_game_has_its_presenter_in_the_application_layer() -> None:
    from application.game_night.game_config_presenter import GAME_PRESENTERS

    assert set(GAME_PRESENTERS) == set(GAME_STATE_TYPES)
    for game in GAME_MODULES:
        assert (BACK_DIR / "application" / game / f"{game}_presenter.py").is_file(), game
        assert type(GAME_PRESENTERS[game]).__module__ == f"application.{game}.{game}_presenter"


def test_the_configuration_accepts_every_supported_game_at_once() -> None:
    from application.game_night.game_night_commands import GameConfigUpsertModel

    payload = {
        "settings": {"game_title": "Soirée", "teams": ["Rouges", "Bleus"]},
        "games": [{"game_key": key, "label": state.label, "round_count": 0} for key, state in GAME_STATE_TYPES.items()],
    }

    assert len(GameConfigUpsertModel.model_validate(payload).to_domain().games) == len(SUPPORTED_GAME_KEYS)
