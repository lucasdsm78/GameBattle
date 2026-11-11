"""Constantes rangées par module et par couche, dans des dossiers `constants/` ; jamais de fichier fourre-tout.

Une constante publique (`NOM` en majuscules, valeur littérale) vit dans le dossier `constants/` de son module :
les règles métier dans `domain/<module>/constants/`, les réglages techniques près de leur code
(`interface/realtime/constants/`, `infrastructure/constants/`…). Une valeur purement locale reste dans son
fichier, privée (`_NOM`). Les catalogues de contenu (`services/*_catalog.py`) gardent leurs données.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from architecture_support import BACK_DIR

LAYERS = ("domain", "application", "infrastructure", "interface")
LITERAL_CALLS = {"frozenset", "tuple", "set"}
ENUM_BASES = {"StrEnum", "IntEnum", "Enum"}
CONSTANT_IMPORTS = {"__future__", "enum"}  # en plus des autres dossiers `constants/`


def _is_literal(node: ast.expr, known: set[str]) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Name):
        return node.id in known
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_is_literal(item, known) for item in node.elts)
    if isinstance(node, ast.Dict):
        return all(key is not None and _is_literal(key, known) and _is_literal(value, known) for key, value in zip(node.keys, node.values))
    if isinstance(node, ast.BinOp):
        return _is_literal(node.left, known) and _is_literal(node.right, known)
    if isinstance(node, ast.UnaryOp):
        return _is_literal(node.operand, known)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in LITERAL_CALLS:
        return not node.keywords and all(_is_literal(argument, known) for argument in node.args)
    return False


def _public_literal_constants(path: Path) -> list[str]:
    known: set[str] = set()
    found = []
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign):
            pairs = [
                pair
                for target in node.targets
                for pair in (
                    zip(target.elts, node.value.elts)
                    if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple)
                    else [(target, node.value)]
                )
            ]
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            pairs = [(node.target, node.value)]
        else:
            continue
        for target, value in pairs:
            if isinstance(target, ast.Name) and target.id.isupper() and not target.id.startswith("_") and _is_literal(value, known):
                found.append(target.id)
                known.add(target.id)
    return found


def _is_catalog(path: Path) -> bool:
    return path.parent.name == "services" and path.name.endswith("_catalog.py")


def _layer_files() -> list[Path]:
    return sorted(path for layer in LAYERS for path in (BACK_DIR / layer).rglob("*.py"))


def _constant_files() -> list[Path]:
    return sorted(path for path in _layer_files() if path.parent.name == "constants")


def _relative(path: Path) -> str:
    return str(path.relative_to(BACK_DIR))


def test_public_constants_live_in_constants_folders() -> None:
    scattered = {
        _relative(path): names
        for path in _layer_files()
        if path.parent.name != "constants" and not _is_catalog(path) and (names := _public_literal_constants(path))
    }

    assert scattered == {}, "à ranger dans un dossier constants/, ou à rendre privé (_NOM) si la valeur est purement locale"


def test_constants_folders_sit_next_to_their_code() -> None:
    """`<couche>/<module>/constants/` ; pour les réglages techniques partagés d'une couche, `<couche>/constants/`."""
    folders = {path.parent for path in _constant_files()}
    misplaced = []
    for folder in sorted(folders):
        parts = folder.relative_to(BACK_DIR).parts
        layer = parts[0]
        if layer in {"domain", "application"}:
            ok = len(parts) == 3 and (BACK_DIR / layer / parts[1]).is_dir()
        else:
            ok = len(parts) in {2, 3}
        if not ok:
            misplaced.append("/".join(parts))

    assert folders, "aucun dossier constants/ trouvé"
    assert misplaced == []


def test_no_catch_all_constants_module() -> None:
    catch_all = [_relative(path) for path in BACK_DIR.glob("*.py") if path.stem == "constants"]
    catch_all += [_relative(path) for path in _layer_files() if path.stem == "constants"]
    catch_all += [_relative(path) for path in _constant_files() if path.name == "__init__.py"]

    assert catch_all == []  # ni `constants.py` fourre-tout, ni point d'export : chaque constante s'importe par son fichier


@pytest.mark.parametrize("path", _constant_files(), ids=_relative)
def test_constants_files_hold_only_constants(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    intruders = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)):
            continue
        if isinstance(node, ast.ImportFrom) and node.module and (node.module in CONSTANT_IMPORTS or ".constants." in node.module):
            continue
        if isinstance(node, ast.ClassDef) and {getattr(base, "id", "") for base in node.bases} & ENUM_BASES:
            if all(isinstance(member, (ast.Assign, ast.Expr)) for member in node.body):
                continue
        intruders.append(f"ligne {node.lineno} : {type(node).__name__}")

    assert intruders == [], "un fichier de constantes ne contient que des valeurs (et des StrEnum), sans logique ni dépendance"


@pytest.mark.parametrize("path", _constant_files(), ids=_relative)
def test_constants_files_are_documented(path: Path) -> None:
    assert ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))), "une phrase pour dire ce que ces valeurs règlent"
