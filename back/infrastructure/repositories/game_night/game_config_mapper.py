from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from functools import cache
from typing import Any, Optional

from domain.game_night.models.game_config import GameConfig
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from domain.game_night.models.session import GameSession
from infrastructure.database.dataclass_codec import decode, init_fields
from infrastructure.repositories.game_night.game_state_repositories import (
    GAME_STATE_REPOSITORIES,
)

_SESSION_FIELDS = ("status", "updated_at", "settings", "games", "rounds")


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


def game_config_from_payload(payload: dict[str, Any], schema_versions: Optional[Mapping[str, int]] = None) -> GameConfig:
    """L'état de chaque jeu passe par le mapper de son module : mise à niveau versionnée, réparation, typage.

    `schema_versions` donne la version de chaque document lu en base ; à défaut, documents à la version courante.
    """
    session = dict(payload.get("session") or {})
    teams = list(payload["settings"].get("teams", []))
    states = {}
    for game_key, repository in GAME_STATE_REPOSITORIES.items():
        if game_key in session:
            mapper = repository.mapper
            states[game_key] = mapper.to_state(session.pop(game_key), (schema_versions or {}).get(game_key, mapper.schema_version), teams)
    config = decode(GameConfig, {**payload, "session": session})
    config.session = replace(config.session, **states)
    config.validate()
    return config


@dataclass(frozen=True, slots=True)
class GameSessionRecord:
    """Forme rangée en base : la ligne commune de la partie et le document de chaque jeu, chacun dans sa table."""

    common: dict[str, Any]
    game_states: dict[str, dict[str, Any]]


@cache
def common_session_fields() -> tuple[str, ...]:
    """Champs de `GameSession` qui ne sont pas l'état d'un jeu : le cycle de vie commun, en colonnes."""
    return tuple(name for name, _ in init_fields(GameSession) if name not in GAME_STATE_TYPES)


def split_payload(payload: dict[str, Any]) -> GameSessionRecord:
    session = payload["session"]
    common = {name: payload[name] for name in _SESSION_FIELDS}
    common.update({_column(name): session[name] for name in common_session_fields()})
    active_round = session.get("active_round")
    common["active_game_key"] = active_round["game_key"] if active_round else None  # colonne dérivée, pour les requêtes
    return GameSessionRecord(common=common, game_states={key: session[key] for key in GAME_STATE_TYPES})


def join_payload(record: GameSessionRecord) -> dict[str, Any]:
    """Inverse de `split_payload`. Un jeu sans ligne (ajouté depuis) reprend son état par défaut."""
    session = {name: record.common[_column(name)] for name in common_session_fields() if _column(name) in record.common}
    session.update(record.game_states)
    return {**{name: record.common[name] for name in _SESSION_FIELDS}, "session": session}


def _column(session_field: str) -> str:
    # `GameSession.updated_at` et `GameConfig.updated_at` coexistent sur la même ligne.
    return "session_updated_at" if session_field == "updated_at" else session_field
