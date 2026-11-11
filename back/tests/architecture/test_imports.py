from __future__ import annotations

import ast
from pathlib import Path

import pytest
from architecture_support import BACK_DIR, GAME_MODULES

from domain.game_night.models.game_registry import GAME_STATE_TYPES
from domain.game_night.models.session import GameSession

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


def _domain_dependencies(module: str) -> set[str]:
    return {
        imported.split(".")[1]
        for path in (BACK_DIR / "domain" / module).rglob("*.py")
        for imported in _imported_modules(path)
        if imported.startswith("domain.") and imported.count(".") >= 1
    }


PRESENTATION_MEMBERS = {"to_dict", "to_payload", "client_views", "shared_view", "display_view", "payload_extras", "private_fields"}


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_layers_only_depend_inwards(layer: str) -> None:
    violations = [
        f"{path.relative_to(BACK_DIR)} -> {module}"
        for path in (BACK_DIR / layer).rglob("*.py")
        for module in _imported_modules(path)
        if module.split(".")[0] in FORBIDDEN_IMPORTS[layer]
    ]

    assert violations == []


@pytest.mark.parametrize("game", GAME_MODULES)
def test_a_game_only_depends_on_the_shared_kernel(game: str) -> None:
    assert _domain_dependencies(game) <= {game, "shared"}


def test_the_shared_kernel_depends_on_no_other_domain_module() -> None:
    assert _domain_dependencies("shared") <= {"shared"}


def test_player_accounts_are_independent_of_the_games() -> None:
    assert _domain_dependencies("accounts") <= {"accounts"}


def test_rooms_only_depend_on_the_shared_kernel() -> None:
    # Les salons connaissent un joueur par `PlayerIdentity`, jamais par le module comptes.
    assert _domain_dependencies("rooms") <= {"rooms", "shared"}


def test_the_domain_knows_nothing_about_client_views() -> None:
    from domain.game_night.models.game_config import GameConfig

    for model in (GameConfig, GameSession, *GAME_STATE_TYPES.values()):
        assert PRESENTATION_MEMBERS.isdisjoint(dir(model)), model.__name__
