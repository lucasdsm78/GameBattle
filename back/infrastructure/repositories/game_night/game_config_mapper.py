from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, is_dataclass
from functools import cache
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from domain.game_night.models.game_config import GameConfig
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from domain.game_night.models.session import GameSession
from infrastructure.repositories.bombe.bombe_state_upgrade import upgrade_bombe_state
from infrastructure.repositories.fair_price.fair_price_state_upgrade import (
    upgrade_fair_price_state,
)
from infrastructure.repositories.memory.memory_state_upgrade import upgrade_memory_state

StateUpgrade = Callable[[dict[str, Any], list[str]], dict[str, Any]]

# Chaque jeu met à niveau ses propres états anciens (dans son dossier) ; la soirée ne fait que les appeler.
GAME_STATE_UPGRADES: dict[str, StateUpgrade] = {
    "bombe": upgrade_bombe_state,
    "memory": upgrade_memory_state,
    "fair_price": upgrade_fair_price_state,
}
NIGHT_FIELDS = ("status", "updated_at", "settings", "games", "rounds")


def game_config_to_payload(config: GameConfig) -> dict[str, Any]:
    """Forme sérialisée de l'agrégat : l'état brut, sans vue client ni événement en attente."""
    return {
        "settings": asdict(config.settings),
        "games": [asdict(game) for game in config.games],
        "rounds": [asdict(round_config) for round_config in config.rounds],
        "session": asdict(config.session),
        "status": config.status,
        "updated_at": config.updated_at,
    }


def game_config_from_payload(payload: dict[str, Any]) -> GameConfig:
    config = _decode(GameConfig, _upgrade_game_states(payload))
    config.validate()
    return config


@dataclass(frozen=True, slots=True)
class GameNightRecord:
    """Forme rangée en base : la ligne commune de la soirée et l'état de chaque jeu, chacun dans sa table."""

    night: dict[str, Any]
    game_states: dict[str, dict[str, Any]]


@cache
def common_session_fields() -> tuple[str, ...]:
    """Champs de `GameSession` qui ne sont pas l'état d'un jeu : le cycle de vie commun, en colonnes."""
    return tuple(name for name, _ in _init_fields(GameSession) if name not in GAME_STATE_TYPES)


def split_payload(payload: dict[str, Any]) -> GameNightRecord:
    session = payload["session"]
    night = {name: payload[name] for name in NIGHT_FIELDS}
    night.update({_column(name): session[name] for name in common_session_fields()})
    return GameNightRecord(night=night, game_states={key: session[key] for key in GAME_STATE_TYPES})


def join_payload(record: GameNightRecord) -> dict[str, Any]:
    """Inverse de `split_payload`. Un jeu sans ligne (ajouté depuis) reprend son état par défaut."""
    session = {name: record.night[_column(name)] for name in common_session_fields() if _column(name) in record.night}
    session.update(record.game_states)
    return {**{name: record.night[name] for name in NIGHT_FIELDS}, "session": session}


def _column(session_field: str) -> str:
    # `GameSession.updated_at` et `GameConfig.updated_at` coexistent sur la même ligne.
    return "session_updated_at" if session_field == "updated_at" else session_field


@cache
def _init_fields(cls: type) -> tuple[tuple[str, Any], ...]:
    hints = get_type_hints(cls)
    return tuple((field.name, hints[field.name]) for field in fields(cls) if field.init)


def _decode(annotation: Any, value: Any) -> Any:
    """Reconstruit récursivement une dataclass ; les clés calculées ou inconnues sont ignorées."""
    origin = get_origin(annotation)
    if origin is list:
        (item_type,) = get_args(annotation)
        return [_decode(item_type, item) for item in value or ()]
    if origin is dict:
        return dict(value or {})
    if value is None:
        return None
    if origin in (Union, UnionType):
        (inner,) = (arg for arg in get_args(annotation) if arg is not NoneType)
        return _decode(inner, value)
    if is_dataclass(annotation):
        return annotation(**{name: _decode(field_type, value[name]) for name, field_type in _init_fields(annotation) if name in value})
    return value


def _upgrade_game_states(payload: dict[str, Any]) -> dict[str, Any]:
    session = dict(payload.get("session") or {})
    teams = list(payload["settings"].get("teams", []))
    for game_key, upgrade in GAME_STATE_UPGRADES.items():
        if game_key in session:
            session[game_key] = upgrade(session[game_key], teams)
    return {**payload, "session": session}
