from __future__ import annotations

import ast
from pathlib import Path

from architecture_support import (
    BACK_DIR,
    DATABASE_DIR,
    DATABASE_MODULE_DIRS,
    GAME_MODULES,
    REPOSITORIES_DIR,
)

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


# Ce qu'un module du domaine peut contenir : ses modèles, ses événements, ses services, ses ports de dépôt et ses
# constantes (règles chiffrées, phases). Rien d'autre : pas de dossier `utils/` ou `helpers/` fourre-tout.
DOMAIN_MODULE_FOLDERS = {"models", "events", "services", "repositories", "constants", "__pycache__"}


DATABASE_TECHNICAL_FILES = {
    "__init__.py", "all_models.py", "database.py", "dataclass_codec.py", "json_document.py", "single_instance_lock.py",
    "schema_version.py", "sql_unit_of_work.py", "upsert.py",
}


def test_every_domain_module_follows_the_same_layout() -> None:
    expected = {"game_night", "shared", "accounts", "rooms", *GAME_MODULES}
    modules = {path.name for path in (BACK_DIR / "domain").iterdir() if path.is_dir() and path.name != "__pycache__"}

    assert modules == expected
    assert all((BACK_DIR / "domain" / module / "models").is_dir() for module in expected)
    unknown = {
        f"{module}/{folder.name}"
        for module in expected
        for folder in (BACK_DIR / "domain" / module).iterdir()
        if folder.is_dir() and folder.name not in DOMAIN_MODULE_FOLDERS
    }
    assert unknown == set()


def test_each_module_holds_one_main_class() -> None:
    crowded = {
        str(path.relative_to(BACK_DIR)): classes
        for layer in ("domain", "application", "infrastructure", "interface")
        for path in (BACK_DIR / layer).rglob("*.py")
        if len(classes := _main_classes(path)) > 1
    }

    assert set(crowded) <= set(SEVERAL_MAIN_CLASSES_ALLOWED), {key: crowded[key] for key in set(crowded) - set(SEVERAL_MAIN_CLASSES_ALLOWED)}


def test_persistence_is_grouped_by_module() -> None:
    accounts = {path.name for path in (DATABASE_DIR / "accounts").glob("*_model.py")}

    assert accounts == {"player_account_model.py", "player_session_model.py"}
    assert {path.name for path in (DATABASE_DIR / "rate_limiting").glob("*.py")} == {"__init__.py", "attempt_model.py", "sql_attempt_counter.py"}
    assert (DATABASE_DIR / "game_sessions" / "game_session_model.py").is_file()
    games = {path.name for path in (DATABASE_DIR / "games").iterdir() if path.is_dir() and path.name not in {"shared", "__pycache__"}}
    assert games == set(GAME_MODULES)
    for game in GAME_MODULES:
        files = {path.name for path in (DATABASE_DIR / "games" / game).glob("*.py")}
        assert files == {"__init__.py", f"{game}_game_model.py", f"{game}_mapper.py", f"{game}_repository.py"}, game


def test_the_database_package_holds_only_module_folders_and_technical_files() -> None:
    # Ni dossier central `models/`, ni modèle posé à la racine : chaque table vit dans le dossier de son module.
    folders = {path.name for path in DATABASE_DIR.iterdir() if path.is_dir() and path.name != "__pycache__"}
    files = {path.name for path in DATABASE_DIR.glob("*.py")}

    assert folders == {*DATABASE_MODULE_DIRS, "games"}
    assert files <= DATABASE_TECHNICAL_FILES


def test_repositories_are_grouped_by_domain() -> None:
    domain_modules = {path.name for path in (BACK_DIR / "domain").iterdir() if path.is_dir() and path.name != "__pycache__"}
    misplaced = [
        str(path.relative_to(REPOSITORIES_DIR))
        for path in REPOSITORIES_DIR.rglob("*.py")
        if len(path.relative_to(REPOSITORIES_DIR).parts) != 2 or path.parent.name not in domain_modules
    ]

    assert misplaced == []
