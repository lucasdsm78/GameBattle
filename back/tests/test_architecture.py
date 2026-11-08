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
        "golden-family.buzzer",
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
    "flash_calc", "right_flag", "golden_family", "fair_price",
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


def test_player_accounts_are_independent_of_the_games() -> None:
    assert _domain_dependencies("accounts") <= {"accounts"}


def test_every_domain_module_follows_the_same_layout() -> None:
    expected = {"game_night", "shared", "accounts", *GAME_MODULES}
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
        assert (BACK_DIR / "application" / game / f"{game}_rules.py").is_file(), f"{game} doit avoir son fichier de règles"
        assert "rules" in vars(type(GAME_PRESENTERS[game])), f"{game} doit déclarer ses règles dans son presenter"


def test_the_configuration_accepts_every_supported_game_at_once() -> None:
    from application.game_night.game_night_commands import GameConfigUpsertModel

    payload = {
        "settings": {"game_title": "Soirée", "teams": ["Rouges", "Bleus"]},
        "games": [{"game_key": key, "label": state.label, "round_count": 0} for key, state in GAME_STATE_TYPES.items()],
    }

    assert len(GameConfigUpsertModel.model_validate(payload).to_domain().games) == len(SUPPORTED_GAME_KEYS)


# Un fichier = une responsabilité : au plus une classe « principale » (au moins deux méthodes) par module. Les petits
# types liés (valeurs, DTO, événements) peuvent l'accompagner. Exceptions assumées, un seul concept chacune :
SEVERAL_MAIN_CLASSES_ALLOWED = {
    "interface/realtime/hub.py": "ClientChannel est la file d'envoi propre au hub de diffusion",
    "infrastructure/extern/usb_buzzer_bridge.py": "script autonome : configuration et pont USB forment un tout",
}


def _main_classes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and sum(isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) for member in node.body) >= 2
    ]


def test_each_module_holds_one_main_class() -> None:
    crowded = {
        str(path.relative_to(BACK_DIR)): classes
        for layer in ("domain", "application", "infrastructure", "interface")
        for path in (BACK_DIR / layer).rglob("*.py")
        if len(classes := _main_classes(path)) > 1
    }

    assert set(crowded) <= set(SEVERAL_MAIN_CLASSES_ALLOWED), {key: crowded[key] for key in set(crowded) - set(SEVERAL_MAIN_CLASSES_ALLOWED)}


# Monolithe modulaire : la persistance est rangée par module. Les comptes dans `database/models/accounts/`, la partie
# commune dans `database/game_sessions/`, chaque jeu dans `database/games/<jeu>/` (table, mapper, dépôt). Un fichier
# n'utilise que les tables des modules que le sien peut connaître ; un autre module passe par un contrat applicatif.
DATABASE_PACKAGE = "infrastructure.database."
ALL_MODELS = "infrastructure.database.all_models"
SCHEMA_ENTRY_POINTS = {"infrastructure/database/database.py", "infrastructure/database/all_models.py"}
DATABASE_DIR = BACK_DIR / "infrastructure" / "database"


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
    """Module propriétaire d'un chemin sous `infrastructure/database` (`models/<m>`, `games/<m>`, `game_sessions`)."""
    if parts[:1] == ("game_sessions",):
        return "game_night"
    if len(parts) >= 2 and parts[0] in {"models", "games"}:
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


def test_persistence_is_grouped_by_module() -> None:
    accounts = {path.name for path in (DATABASE_DIR / "models" / "accounts").glob("*_model.py")}

    assert not (DATABASE_DIR / "models.py").exists()
    assert accounts == {"player_account_model.py", "player_session_model.py", "auth_attempt_model.py"}
    assert (DATABASE_DIR / "game_sessions" / "game_session_model.py").is_file()
    games = {path.name for path in (DATABASE_DIR / "games").iterdir() if path.is_dir() and path.name not in {"shared", "__pycache__"}}
    assert games == set(GAME_MODULES)
    for game in GAME_MODULES:
        files = {path.name for path in (DATABASE_DIR / "games" / game).glob("*.py")}
        assert files == {"__init__.py", f"{game}_game_model.py", f"{game}_mapper.py", f"{game}_repository.py"}, game


def test_every_game_mapper_converts_to_its_own_domain_state() -> None:
    from infrastructure.repositories.game_night.game_state_repositories import (
        GAME_STATE_REPOSITORIES,
    )

    assert set(GAME_STATE_REPOSITORIES) == set(GAME_STATE_TYPES)
    for game, repository in GAME_STATE_REPOSITORIES.items():
        assert repository.mapper.state_type is GAME_STATE_TYPES[game], game
        assert repository.model.__tablename__ == f"{game}_games", game
        assert type(repository).__module__ == f"infrastructure.database.games.{game}.{game}_repository", game


REPOSITORIES_DIR = BACK_DIR / "infrastructure" / "repositories"


def test_repositories_are_grouped_by_domain() -> None:
    domain_modules = {path.name for path in (BACK_DIR / "domain").iterdir() if path.is_dir() and path.name != "__pycache__"}
    misplaced = [
        str(path.relative_to(REPOSITORIES_DIR))
        for path in REPOSITORIES_DIR.rglob("*.py")
        if len(path.relative_to(REPOSITORIES_DIR).parts) != 2 or path.parent.name not in domain_modules
    ]

    assert misplaced == []


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
