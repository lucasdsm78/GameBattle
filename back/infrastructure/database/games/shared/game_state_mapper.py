from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import Any, ClassVar, Generic, TypeVar

from domain.shared.models.game_state import GameState
from infrastructure.database.dataclass_codec import decode

StateT = TypeVar("StateT", bound=GameState)
DocumentMigration = Callable[[dict[str, Any]], dict[str, Any]]


class GameStateMapper(Generic[StateT]):
    """Document JSONB <-> état typé d'un jeu. Le domaine ne voit jamais le dictionnaire.

    `migrations[n]` fait passer un document de la version `n` à `n + 1` : un document ancien est mis à niveau
    étape par étape au chargement, puis réécrit à la version courante à la prochaine sauvegarde.
    `repair` corrige des données encore au bon format mais devenues invalides (objet retiré d'un catalogue…).
    """

    state_type: ClassVar[type[GameState]]
    schema_version: ClassVar[int] = 1
    migrations: ClassVar[dict[int, DocumentMigration]] = {}

    def to_document(self, state: StateT) -> dict[str, Any]:
        return asdict(state)

    def to_state(self, document: dict[str, Any], schema_version: int, teams: list[str]) -> StateT:
        return decode(self.state_type, self.repair(self.migrate(document, schema_version), teams))

    def migrate(self, document: dict[str, Any], schema_version: int) -> dict[str, Any]:
        if schema_version > self.schema_version:
            raise ValueError(
                f"{self.state_type.__name__} : document en version {schema_version}, plus récent que ce code "
                f"(version {self.schema_version}). Déployez la version de l'API qui l'a écrit."
            )
        for version in range(schema_version, self.schema_version):
            document = self.migrations[version](document)
        return document

    def repair(self, document: dict[str, Any], teams: list[str]) -> dict[str, Any]:
        return document
