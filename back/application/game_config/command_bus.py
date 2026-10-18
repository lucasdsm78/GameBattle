from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from inspect import isawaitable
import time
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ValidationError

from application.game_config.errors import CommandNotAllowedError, InvalidCommandPayloadError, UnknownCommandError
from application.game_config.snapshot import ClientRole, GameConfigSnapshot
from domain.game_config.model.game_config import GameConfig
from domain.game_config.repository.game_config_repository import GameConfigRepository

if TYPE_CHECKING:
    from application.blindtest.playlist_service import BlindtestPlaylistService

CONTROLLER_ONLY = frozenset({ClientRole.CONTROLLER})
CONTROLLER_AND_DISPLAY = frozenset({ClientRole.CONTROLLER, ClientRole.DISPLAY})
HARDWARE_ONLY = frozenset({ClientRole.HARDWARE})
SYSTEM_ONLY = frozenset({ClientRole.SYSTEM})

DISPLAY_READ_ONLY_MESSAGE = "Le client display est en lecture seule."


def wall_clock_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True, slots=True)
class CommandContext:
    now_ms: int
    playlists: BlindtestPlaylistService


CommandHandler = Callable[[GameConfig, Any, CommandContext], GameConfig | Awaitable[GameConfig]]


@dataclass(frozen=True, slots=True)
class CommandSpec:
    name: str
    handler: CommandHandler
    payload_model: type[BaseModel] | None = None
    roles: frozenset[ClientRole] = CONTROLLER_ONLY


class SnapshotPublisher(Protocol):
    def publish(self, snapshot: GameConfigSnapshot) -> None:
        """Diffuse sans attendre : appelé sous le verrou de mutation pour garantir l'ordre des états."""


class GameCommandBus:
    """Point d'entrée unique des écritures : autorise, valide, applique, persiste puis diffuse.

    Une commande sans effet (l'agrégat renvoie `self`) n'écrit ni ne diffuse rien : `execute` renvoie `None`.
    """

    def __init__(
        self,
        repository: GameConfigRepository,
        playlists: BlindtestPlaylistService,
        publisher: SnapshotPublisher,
        commands: Iterable[CommandSpec],
        clock: Callable[[], int] = wall_clock_ms,
    ) -> None:
        self._repository = repository
        self._playlists = playlists
        self._publisher = publisher
        self._clock = clock
        self._commands: dict[str, CommandSpec] = {}
        for spec in commands:
            if spec.name in self._commands:
                raise ValueError(f"Commande déclarée deux fois : {spec.name}")
            self._commands[spec.name] = spec

    @property
    def command_names(self) -> frozenset[str]:
        return frozenset(self._commands)

    async def execute(
        self, name: str, payload: Mapping[str, Any] | BaseModel | None, role: ClientRole
    ) -> GameConfigSnapshot | None:
        spec = self._authorize(name, role)
        command = self._parse(spec, payload)
        async with self._repository.mutation_lock:
            current = await self._repository.get_current()
            result = spec.handler(current, command, CommandContext(now_ms=self._clock(), playlists=self._playlists))
            updated = await result if isawaitable(result) else result
            if updated is current:
                return None
            updated.validate()
            await self._repository.save(updated)
            snapshot = GameConfigSnapshot.from_domain(updated)
            self._publisher.publish(snapshot)
        return snapshot

    def _authorize(self, name: str, role: ClientRole) -> CommandSpec:
        spec = self._commands.get(name)
        if spec is None:
            raise UnknownCommandError("Type d'évènement non supporté.")
        if role not in spec.roles:
            raise CommandNotAllowedError(
                DISPLAY_READ_ONLY_MESSAGE if role is ClientRole.DISPLAY else "Commande non autorisée pour ce client."
            )
        return spec

    @staticmethod
    def _parse(spec: CommandSpec, payload: Mapping[str, Any] | BaseModel | None) -> BaseModel | None:
        if spec.payload_model is None:
            return None
        if isinstance(payload, spec.payload_model):
            return payload
        try:
            return spec.payload_model.model_validate(payload or {})
        except ValidationError as exc:
            fields = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
            detail = f" ({', '.join(fields)})" if fields else ""
            raise InvalidCommandPayloadError(f"Données invalides pour « {spec.name} »{detail}.") from None
