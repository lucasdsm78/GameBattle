from __future__ import annotations

import ast
from pathlib import Path
from typing import get_args

from architecture_support import (
    BACK_DIR,
    DATABASE_DIR,
    DATABASE_MODULE_DIRS,
    GAME_MODULES,
    REPOSITORIES_DIR,
)

from application.game_night.commands.fields import GameKey
from domain.game_night.constants.game_night_limits import SUPPORTED_GAME_KEYS
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from domain.game_night.models.session import GameSession

DATABASE_PACKAGE = "infrastructure.database."


ALL_MODELS = "infrastructure.database.all_models"


SCHEMA_ENTRY_POINTS = {"infrastructure/database/database.py", "infrastructure/database/all_models.py"}


def _imported_names(path: Path) -> set[str]:
    """Modules importés, y compris `paquet.nom` pour `from paquet import nom` (un sous-module peut s'importer ainsi)."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def _module_of(parts: tuple[str, ...]) -> str | None:
    """Module propriétaire d'un chemin sous `infrastructure/database` (`accounts`, `game_sessions`, `games/<jeu>`)."""
    if parts[:1] and parts[0] in DATABASE_MODULE_DIRS:
        return DATABASE_MODULE_DIRS[parts[0]]
    if len(parts) >= 2 and parts[0] == "games":
        return parts[1]
    return None


def _model_modules(path: Path) -> set[str]:
    modules = set()
    for name in _imported_names(path):
        if name.startswith(DATABASE_PACKAGE) and (module := _module_of(tuple(name.removeprefix(DATABASE_PACKAGE).split(".")))):
            modules.add(module)
    return modules


def _layer_files() -> list[Path]:
    return [path for layer in ("domain", "application", "infrastructure", "interface") for path in (BACK_DIR / layer).rglob("*.py")]


def _allowed_modules(module: str) -> set[str]:
    """Même direction que le domaine : un jeu ne connaît que lui (et le noyau partagé) ; la partie compose les jeux."""
    return {module, "shared"} | (set(GAME_MODULES) if module == "game_night" else set())


def _owning_module(path: Path) -> str | None:
    if DATABASE_DIR in path.parents:
        return _module_of(path.relative_to(DATABASE_DIR).parts[:-1] or ("",))
    if (BACK_DIR / "infrastructure" / "repositories") in path.parents:
        return path.relative_to(BACK_DIR / "infrastructure" / "repositories").parts[0]
    return None


def test_every_game_is_registered_consistently_across_layers() -> None:
    session_fields = set(GameSession.__dataclass_fields__)

    assert set(GAME_STATE_TYPES) == SUPPORTED_GAME_KEYS == set(get_args(GameKey))
    assert set(GAME_STATE_TYPES) <= session_fields


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


def test_every_game_has_its_presenter_in_the_application_layer() -> None:
    from application.game_night.game_config_presenter import GAME_PRESENTERS

    assert set(GAME_PRESENTERS) == set(GAME_STATE_TYPES)
    for game in GAME_MODULES:
        assert (BACK_DIR / "application" / game / f"{game}_presenter.py").is_file(), game
        assert type(GAME_PRESENTERS[game]).__module__ == f"application.{game}.{game}_presenter"
        assert (BACK_DIR / "application" / game / f"{game}_rules.py").is_file(), f"{game} doit avoir son fichier de règles"
        assert "rules" in vars(type(GAME_PRESENTERS[game])), f"{game} doit déclarer ses règles dans son presenter"


def test_the_configuration_accepts_every_supported_game_at_once() -> None:
    from application.game_night.commands.game_config_upsert import GameConfigUpsertModel

    payload = {
        "settings": {"game_title": "Soirée", "teams": ["Rouges", "Bleus"]},
        "games": [{"game_key": key, "label": state.label, "round_count": 0} for key, state in GAME_STATE_TYPES.items()],
    }

    assert len(GameConfigUpsertModel.model_validate(payload).to_domain().games) == len(SUPPORTED_GAME_KEYS)


def test_a_file_only_uses_the_orm_models_its_module_may_know() -> None:
    violations = {}
    for path in _layer_files():
        relative = str(path.relative_to(BACK_DIR))
        used = _model_modules(path) - {"shared"}
        if relative in SCHEMA_ENTRY_POINTS or not used:
            continue
        module = _owning_module(path)
        if (module is None and len(used) > 1) or (module is not None and not used <= _allowed_modules(module)):
            violations[relative] = sorted(used)

    assert violations == {}


def test_only_the_schema_uses_the_aggregate_of_all_models() -> None:
    users = {str(path.relative_to(BACK_DIR)) for path in _layer_files() if ALL_MODELS in _imported_names(path)}

    assert users <= SCHEMA_ENTRY_POINTS


def test_every_game_mapper_converts_to_its_own_domain_state() -> None:
    from infrastructure.repositories.game_night.game_state_repositories import (
        GAME_STATE_REPOSITORIES,
    )

    assert set(GAME_STATE_REPOSITORIES) == set(GAME_STATE_TYPES)
    for game, repository in GAME_STATE_REPOSITORIES.items():
        assert repository.mapper.state_type is GAME_STATE_TYPES[game], game
        assert repository.model.__tablename__ == f"{game}_games", game
        assert type(repository).__module__ == f"infrastructure.database.games.{game}.{game}_repository", game


def test_a_domain_repository_only_imports_the_repositories_its_module_may_know() -> None:
    crossing = {
        str(path.relative_to(REPOSITORIES_DIR)): sorted(foreign)
        for path in REPOSITORIES_DIR.rglob("*.py")
        if (
            foreign := {
                name.split(".")[2]
                for name in _imported_names(path)
                if name.startswith("infrastructure.repositories.")
            }
            - _allowed_modules(path.parent.name)
        )
    }

    assert crossing == {}
