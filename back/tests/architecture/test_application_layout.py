"""Rangement de la couche application : une commande, une vue ou un résultat par fichier, nommé d'après son contenu."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from architecture_support import BACK_DIR

APPLICATION_DIR = BACK_DIR / "application"
SHARED_TYPES_FILE = "fields.py"  # types partagés par les commandes d'un module (`TeamName`, `GameKey`…)
ONE_ENTRY_FOLDERS = ("presenters", "views")  # une vue (fonction) ou un résultat (dataclass) par fichier


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _classes(path: Path) -> list[str]:
    return [node.name for node in _tree(path).body if isinstance(node, ast.ClassDef)]


def _public_definitions(path: Path) -> list[str]:
    return [
        node.name
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_")
    ]


def _relative(path: Path) -> str:
    return str(path.relative_to(APPLICATION_DIR))


def _modules() -> list[Path]:
    return sorted(path for path in APPLICATION_DIR.iterdir() if path.is_dir() and path.name != "__pycache__")


def test_application_packages_are_namespace_packages() -> None:
    # Pas de `__init__.py` : chaque classe s'importe par son chemin complet, sans point d'export qui regroupe.
    assert sorted(_relative(path) for path in APPLICATION_DIR.rglob("__init__.py")) == []


@pytest.mark.parametrize("module", _modules(), ids=lambda path: path.name)
def test_a_module_keeps_its_commands_in_one_place(module: Path) -> None:
    """Une seule commande : `<module>_commands.py`. Plusieurs : un dossier `commands/`, une par fichier. Jamais les deux."""
    single_files = sorted(module.glob("*_commands.py"))

    assert not ((module / "commands").is_dir() and single_files), "commands/ ou <module>_commands.py, pas les deux"
    for path in single_files:
        assert len(_classes(path)) == 1, f"{_relative(path)} : plusieurs commandes → un dossier commands/, une par fichier"


def test_each_command_has_its_own_file_named_after_it() -> None:
    misplaced = []
    for path in sorted(APPLICATION_DIR.rglob("commands/*.py")):
        classes = _classes(path)
        if path.name == SHARED_TYPES_FILE:
            if classes:
                misplaced.append(f"{_relative(path)} : {SHARED_TYPES_FILE} ne contient que des types, pas de classe")
            continue
        names = {_snake(name) for name in classes} | {_snake(re.sub(r"(Command|Model)$", "", name)) for name in classes}
        if len(classes) != 1 or path.stem not in names:
            misplaced.append(f"{_relative(path)} : {classes}")

    assert misplaced == []


@pytest.mark.parametrize("folder", ONE_ENTRY_FOLDERS)
def test_presenters_and_views_expose_one_entry_per_file(folder: str) -> None:
    files = sorted(APPLICATION_DIR.rglob(f"{folder}/*.py"))
    crowded = {
        _relative(path): entries
        for path in files
        if (entries := _public_definitions(path)) != [path.stem] and [_snake(name) for name in entries] != [path.stem]
    }

    assert files, f"aucun dossier {folder}/ trouvé"
    assert crowded == {}
