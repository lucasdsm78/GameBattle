"""Lectures et écritures séparées : un cas d'usage écrit (`*CommandUseCase`) ou lit (`*QueryUseCase`), jamais les deux."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from architecture_support import BACK_DIR

APPLICATION_DIR = BACK_DIR / "application"
SHARED_COMMAND_BASE = "shared/command_usecase.py"  # la base commune des cas d'usage d'écriture des jeux

# Appels qui écrivent : validation de transaction, écritures des dépôts, de l'outbox et des compteurs, réveil du relais.
WRITE_CALLS = {"commit", "add", "save", "save_expiry", "save_password_hash", "delete", "delete_expired", "purge", "append", "notify", "hit", "reset"}

# Seule écriture permise à une lecture, et pourquoi.
QUERIES_ALLOWED_TO_RESERVE_ATTEMPTS = {
    "rooms/room_query_usecase.py": "l'aperçu d'invitation compte les essais par IP : un code se devinerait sinon par essais successifs",
}

# Routes de lecture (GET, flux temps réel en lecture seule) qui ont malgré tout besoin d'une écriture, et pourquoi.
READ_ROUTES_ALLOWED_TO_WRITE = {
    "/api/accounts/me": "prolonge la session d'un joueur actif quand elle est due (environ tous les 15 jours)",
}
READ_ONLY_WEBSOCKETS = {"/ws/rooms/current"}


def _application_files() -> list[Path]:
    return sorted(APPLICATION_DIR.rglob("*.py"))


def _relative(path: Path) -> str:
    return str(path.relative_to(APPLICATION_DIR))


def _query_files() -> list[Path]:
    return sorted(APPLICATION_DIR.rglob("*_query_usecase.py"))


def _called_names(path: Path) -> list[tuple[str, int]]:
    """Noms appelés dans le fichier : `objet.methode(...)` donne `methode`, `fonction(...)` donne `fonction`."""
    calls = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.append((node.func.attr, node.lineno))
            elif isinstance(node.func, ast.Name):
                calls.append((node.func.id, node.lineno))
    return calls


def test_use_case_files_say_whether_they_write_or_read() -> None:
    misnamed = [
        _relative(path)
        for path in _application_files()
        if "usecase" in path.stem
        and not path.stem.endswith(("_command_usecase", "_query_usecase"))
        and _relative(path) != SHARED_COMMAND_BASE
    ]

    assert misnamed == []


def test_use_case_classes_match_their_file() -> None:
    mismatched = []
    for path in _application_files():
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not (isinstance(node, ast.ClassDef) and node.name.endswith("UseCase")):
                continue
            if _relative(path) == SHARED_COMMAND_BASE and node.name == "CommandUseCase":
                continue
            kind = path.stem.rsplit("_", 2)[-2] if path.stem.endswith(("_command_usecase", "_query_usecase")) else None
            if kind is None or not node.name.endswith(f"{kind.capitalize()}UseCase"):
                mismatched.append(f"{_relative(path)}: {node.name}")

    assert mismatched == []


@pytest.mark.parametrize("path", _query_files(), ids=_relative)
def test_queries_never_write(path: Path) -> None:
    writes = [f"ligne {line} : {name}()" for name, line in _called_names(path) if name in WRITE_CALLS]
    source = path.read_text(encoding="utf-8")

    assert writes == []
    assert "outbox" not in source and "notifier" not in source  # une lecture ne publie aucun événement


def test_only_documented_queries_reserve_attempts() -> None:
    reserving = {_relative(path) for path in _query_files() if any(name == "reserve_attempts" for name, _ in _called_names(path))}

    assert reserving == set(QUERIES_ALLOWED_TO_RESERVE_ATTEMPTS)


def _command_providers() -> set[str]:
    """Fournisseurs de dépendances qui donnent accès aux écritures (les jeux passent par `game_use_cases`)."""
    from interface.dependencies import container

    by_name = {name for name in vars(container) if name.endswith("_command_usecase")}
    return by_name | {"game_use_cases", "game_night_use_case", "blindtest_use_case", "realtime_dispatcher"}


def _dependency_calls(dependant: object) -> set[str]:
    calls = set()
    for dependency in getattr(dependant, "dependencies", ()):
        if dependency.call is not None:
            calls.add(getattr(dependency.call, "__name__", ""))
        calls |= _dependency_calls(dependency)
    return calls


def test_read_routes_only_reach_queries() -> None:
    from fastapi.routing import APIRoute, APIWebSocketRoute

    from infrastructure.config import Settings
    from main import create_app

    settings = Settings(
        _env_file=None, controller_token="c" * 32, display_token="d" * 32, hardware_token="h" * 32, rate_limit_secret="r" * 64
    )
    commands = _command_providers()
    reads = [
        route
        for route in create_app(settings).routes
        if (isinstance(route, APIRoute) and route.methods == {"GET"}) or (isinstance(route, APIWebSocketRoute) and route.path in READ_ONLY_WEBSOCKETS)
    ]
    writing = {route.path: sorted(_dependency_calls(route.dependant) & commands) for route in reads}

    assert {path: used for path, used in writing.items() if used and path not in READ_ROUTES_ALLOWED_TO_WRITE} == {}
    assert all(writing.get(path) for path in READ_ROUTES_ALLOWED_TO_WRITE), "exception devenue inutile : à retirer"
    assert {route.path for route in reads} >= READ_ONLY_WEBSOCKETS  # le flux des salons est bien contrôlé
