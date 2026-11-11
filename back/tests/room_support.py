from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
from types import TracebackType
from typing import Any, Optional, Self

from account_support import Clock, InMemoryAttempts

from application.rooms.room_unit_of_work import RoomUnitOfWork
from application.rooms.room_usecase import CODE_ALPHABET, CODE_LENGTH, RoomUseCase
from application.shared.outbox import Outbox, OutboxNotifier
from application.shared.player_identity import PlayerIdentity
from domain.rooms.models.room import Room
from domain.rooms.repositories.room_repository import RoomRepository
from domain.shared.events.domain_event import DomainEvent
from exceptions import ConcurrentModificationError
from infrastructure.database.outbox.outbox_store import PendingEvent

ALICE = PlayerIdentity(account_id="11111111-1111-4111-8111-111111111111", pseudo="Alice")
BOB = PlayerIdentity(account_id="22222222-2222-4222-8222-222222222222", pseudo="Bob")
CHLOE = PlayerIdentity(account_id="33333333-3333-4333-8333-333333333333", pseudo="Chloé")
IP = "203.0.113.7"


@dataclass
class RoomStore:
    """La « base » des salons en mémoire : salons, outbox et compteurs d'essais."""

    rooms: dict[str, Room] = field(default_factory=dict)
    outbox: list[PendingEvent] = field(default_factory=list)
    attempts: dict[str, tuple[int, int]] = field(default_factory=dict)

    def copy(self) -> RoomStore:
        return RoomStore(dict(self.rooms), list(self.outbox), dict(self.attempts))


class InMemoryRooms(RoomRepository):
    """Même contrat que le dépôt SQL : verrou optimiste, code et appartenance uniques."""

    def __init__(self, data: RoomStore, conflicts: list[int]) -> None:
        self._data = data
        self._conflicts = conflicts  # nombre d'écritures à faire échouer, pour simuler une course

    async def get(self, room_id: str) -> Optional[Room]:
        return self._data.rooms.get(room_id)

    async def get_by_code(self, code: str) -> Optional[Room]:
        return next((room for room in self._data.rooms.values() if room.code == code), None)

    async def find_by_member(self, account_id: str) -> Optional[Room]:
        return next((room for room in self._data.rooms.values() if room.member(account_id)), None)

    async def list_open_public(self, limit: int) -> list[Room]:
        rooms = [room for room in self._data.rooms.values() if room.visibility == "public" and room.status == "lobby"]
        return sorted(rooms, key=lambda room: room.created_at_ms, reverse=True)[:limit]

    async def list_inactive(self, updated_before_ms: int, limit: int) -> list[Room]:
        return [room for room in self._data.rooms.values() if room.status == "lobby" and room.updated_at_ms < updated_before_ms][:limit]

    async def add(self, room: Room) -> Room:
        self._maybe_conflict()
        taken = {member.account_id for other in self._data.rooms.values() for member in other.members}
        if await self.get_by_code(room.code) or taken & {member.account_id for member in room.members}:
            raise ConcurrentModificationError()
        self._data.rooms[room.id] = saved = replace(room, version=1)
        return saved

    async def save(self, room: Room) -> Room:
        self._maybe_conflict()
        stored = self._data.rooms.get(room.id)
        if stored is None or stored.version != room.version:
            raise ConcurrentModificationError()
        self._data.rooms[room.id] = saved = replace(room, version=room.version + 1)
        return saved

    async def delete(self, room: Room) -> None:
        stored = self._data.rooms.get(room.id)
        if stored is None or stored.version != room.version:
            raise ConcurrentModificationError()
        del self._data.rooms[room.id]

    def _maybe_conflict(self) -> None:
        if self._conflicts and self._conflicts[0] > 0:
            self._conflicts[0] -= 1
            raise ConcurrentModificationError()


class InMemoryOutbox(Outbox):
    def __init__(self, data: RoomStore) -> None:
        self._data = data

    async def append(self, stream: str, events: Sequence[DomainEvent], audience: Optional[str] = None) -> None:
        for event in events:
            self._data.outbox.append(PendingEvent(len(self._data.outbox) + 1, stream, event.name, asdict(event), audience))


class InMemoryRoomUnitOfWork(RoomUnitOfWork):
    """Travaille sur une copie : seul `commit()` publie, comme une vraie transaction."""

    def __init__(self, store: RoomStore, conflicts: list[int]) -> None:
        self._store = store
        self._conflicts = conflicts

    async def __aenter__(self) -> Self:
        self._work = self._store.copy()
        self.rooms = InMemoryRooms(self._work, self._conflicts)
        self.outbox = InMemoryOutbox(self._work)
        self.attempts = InMemoryAttempts(self._work)  # type: ignore[arg-type]  (même forme : un dict `attempts`)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        return None

    async def commit(self) -> None:
        committed = self._work.copy()
        self._store.rooms, self._store.outbox, self._store.attempts = committed.rooms, committed.outbox, committed.attempts


class CountingNotifier(OutboxNotifier):
    def __init__(self, then: Optional[OutboxNotifier] = None) -> None:
        self.calls = 0
        self._then = then

    def notify(self) -> None:
        self.calls += 1
        if self._then is not None:
            self._then.notify()


class InMemoryOutboxStore:
    """Côté relais, sur la même « base » que l'unité de travail."""

    def __init__(self, store: RoomStore) -> None:
        self._store = store
        self.published: set[int] = set()

    async def pending(self, limit: int) -> list[PendingEvent]:
        return [event for event in self._store.outbox if event.id not in self.published][:limit]

    async def mark_published(self, event_ids: list[int], now_ms: int) -> None:
        self.published.update(event_ids)

    async def purge_published(self, published_before_ms: int) -> None:
        return None


def sample_code(index: int) -> str:
    """Codes déterministes et valides (même alphabet, même longueur que les vrais)."""
    return "".join(CODE_ALPHABET[(index // len(CODE_ALPHABET) ** rank) % len(CODE_ALPHABET)] for rank in range(CODE_LENGTH))


@dataclass
class RoomsHarness:
    use_case: RoomUseCase
    store: RoomStore
    clock: Clock
    notifier: CountingNotifier
    conflicts: list[int]


def build_rooms(codes: Optional[list[str]] = None, *, relay: Optional[OutboxNotifier] = None) -> RoomsHarness:
    """`relay` : un notifieur à prévenir en plus du compteur (le vrai relais, pour les tests temps réel)."""
    store, clock, notifier, conflicts = RoomStore(), Clock(), CountingNotifier(relay), [0]
    sequence = iter(codes or (sample_code(index) for index in range(1, 10_000)))
    use_case = RoomUseCase(
        lambda: InMemoryRoomUnitOfWork(store, conflicts), notifier=notifier, clock=clock, new_code=lambda: next(sequence)
    )
    return RoomsHarness(use_case, store, clock, notifier, conflicts)


def events_of(store: RoomStore) -> list[tuple[str, dict[str, Any]]]:
    return [(event.event_type, event.payload) for event in store.outbox]
