from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from functools import cache
from types import NoneType, UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from domain.game_night.models.game_config import GameConfig
from domain.memory.models.memory_state import MEMORY_RULES_VERSION


def game_config_to_payload(config: GameConfig) -> dict[str, Any]:
    """Forme persistée : l'état brut de l'agrégat, sans vue client ni événement en attente."""
    return {
        "settings": asdict(config.settings),
        "games": [asdict(game) for game in config.games],
        "rounds": [asdict(round_config) for round_config in config.rounds],
        "session": asdict(config.session),
        "status": config.status,
        "updated_at": config.updated_at,
    }


def game_config_from_payload(payload: dict[str, Any]) -> GameConfig:
    config = _decode(GameConfig, _upgrade_legacy_payload(payload))
    config.validate()
    return config


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


def _upgrade_legacy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    session = dict(payload.get("session") or {})
    teams = list(payload["settings"].get("teams", []))
    if "bombe" in session:
        session["bombe"] = _upgrade_bombe(session["bombe"], teams)
    if "memory" in session:
        session["memory"] = _upgrade_memory(session["memory"], teams)
    return {**payload, "session": session}


def _upgrade_bombe(bombe: dict[str, Any], teams: list[str]) -> dict[str, Any]:
    """Les anciennes parties en cours n'enregistraient ni pénalités ni équipes en lice."""
    phase = bombe.get("phase", "idle")
    if phase == "idle":
        return bombe
    upgraded = dict(bombe)
    if not bombe.get("scores"):
        upgraded["scores"] = {team: 0 for team in teams}
    if not bombe.get("eligible_team_indices") and phase in {"awaiting_roll", "rolling", "running"}:
        upgraded["eligible_team_indices"] = list(range(len(teams)))
    return upgraded


def _upgrade_memory(memory: dict[str, Any], teams: list[str]) -> dict[str, Any]:
    """Les règles v1 ne sont pas rejouables : on ne conserve qu'un éventuel vainqueur."""
    if memory.get("rules_version") == MEMORY_RULES_VERSION:
        return memory
    winner = memory.get("winner_team")
    if memory.get("phase") == "finished" and winner in teams:
        winner_index = teams.index(winner)
        return {
            "phase": "finished",
            "current_team_index": winner_index,
            "qualified_team_indices": [winner_index],
            "disqualified_teams": [team for team in teams if team != winner],
            "winner_team": winner,
        }
    return {}
