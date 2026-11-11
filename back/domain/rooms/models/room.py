from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from domain.rooms.events import HostChanged, PlayerJoined, PlayerLeft, RoomClosed, RoomOpened, TeamChanged
from domain.rooms.models.room_member import RoomMember
from domain.shared.events.domain_event import DomainEvent
from exceptions import RoomFullError, RoomRuleError

VISIBILITIES = frozenset({"public", "private"})
FORMATS = frozenset({"solo", "teams"})
TEAM_NAMES = ("Rouges", "Bleus", "Verts", "Jaunes")
MIN_TEAMS, MAX_TEAMS = 2, len(TEAM_NAMES)
PLAYERS_PER_TEAM = 4
SOLO_PLAYERS = 2  # 1 contre 1


@dataclass(frozen=True, slots=True)
class Room:
    """Racine d'agrégat d'un salon : qui joue, dans quelle équipe, qui l'anime, et s'il reste de la place.

    Immuable : chaque action renvoie un nouveau salon, avec les événements qu'elle a produits dans
    `pending_events` (publiés via l'outbox après l'écriture). `version` sert au verrou optimiste.
    """

    id: str
    code: str  # secret d'invitation : le lien `/join/<code>`
    visibility: str
    format: str
    teams: tuple[str, ...]  # vide en solo
    host_account_id: str
    members: tuple[RoomMember, ...]
    created_at_ms: int
    updated_at_ms: int
    status: str = "lobby"
    version: int = 0  # 0 : pas encore écrit
    pending_events: tuple[DomainEvent, ...] = field(default=(), compare=False, repr=False)

    @classmethod
    def open(
        cls, *, room_id: str, code: str, visibility: str, format: str, team_count: int, host_account_id: str, host_pseudo: str, now_ms: int
    ) -> Room:
        if visibility not in VISIBILITIES or format not in FORMATS:
            raise RoomRuleError("Type de partie inconnu.")
        if format == "teams" and not MIN_TEAMS <= team_count <= MAX_TEAMS:
            raise RoomRuleError(f"Une partie en équipes se joue de {MIN_TEAMS} à {MAX_TEAMS} équipes.")
        room = cls(
            id=room_id,
            code=code,
            visibility=visibility,
            format=format,
            teams=TEAM_NAMES[:team_count] if format == "teams" else (),
            host_account_id=host_account_id,
            members=(),
            created_at_ms=now_ms,
            updated_at_ms=now_ms,
            pending_events=(RoomOpened(visibility=visibility, format=format, host=host_pseudo),),
        )
        return room.join(host_account_id, host_pseudo, now_ms)

    # --- Lecture ---

    @property
    def capacity(self) -> int:
        return SOLO_PLAYERS if self.format == "solo" else len(self.teams) * PLAYERS_PER_TEAM

    @property
    def is_full(self) -> bool:
        return len(self.members) >= self.capacity

    @property
    def team_choice_allowed(self) -> bool:
        """Choisir son équipe : seulement dans une partie privée en équipes (entre amis, via le lien)."""
        return self.format == "teams" and self.visibility == "private"

    def member(self, account_id: str) -> Optional[RoomMember]:
        return next((member for member in self.members if member.account_id == account_id), None)

    def team_size(self, team: str) -> int:
        return sum(member.team == team for member in self.members)

    def has_room_in(self, team: str) -> bool:
        return team in self.teams and self.team_size(team) < PLAYERS_PER_TEAM

    # --- Actions ---

    def join(self, account_id: str, pseudo: str, now_ms: int, *, team: Optional[str] = None) -> Room:
        """Entrer dans le salon. Déjà membre : rien ne change (un double clic ne fait pas deux entrées)."""
        if self.member(account_id) is not None:
            return self
        if self.status != "lobby":
            raise RoomRuleError("La partie a déjà commencé.")
        if self.is_full:
            raise RoomFullError("Ce salon est complet.")
        assigned = pseudo if self.format == "solo" else self._team_for_newcomer(team)
        member = RoomMember(account_id=account_id, pseudo=pseudo, team=assigned, joined_at_ms=now_ms)
        return self._changed(now_ms, PlayerJoined(pseudo=pseudo, team=assigned), members=(*self.members, member))

    def change_team(self, account_id: str, team: str, now_ms: int) -> Room:
        member = self._require_member(account_id)
        if not self.team_choice_allowed:
            raise RoomRuleError("Les équipes ne se choisissent que dans une partie privée en équipes.")
        if member.team == team:
            return self
        if not self.has_room_in(team):
            raise RoomFullError("Cette équipe est complète.") if team in self.teams else RoomRuleError("Équipe inconnue.")
        members = tuple(replace(m, team=team) if m.account_id == account_id else m for m in self.members)
        return self._changed(now_ms, TeamChanged(pseudo=member.pseudo, team=team), members=members)

    def leave(self, account_id: str, now_ms: int) -> Room:
        """Quitter. L'hôte qui part laisse la main au plus ancien membre ; le dernier qui part ferme le salon."""
        member = self.member(account_id)
        if member is None:
            return self
        members = tuple(m for m in self.members if m.account_id != account_id)
        events: list[DomainEvent] = [PlayerLeft(pseudo=member.pseudo)]
        if not members:
            events.append(RoomClosed(reason="empty"))
            return self._changed(now_ms, *events, members=(), status="closed")
        host_account_id = self.host_account_id
        if account_id == host_account_id:
            successor = min(members, key=lambda m: m.joined_at_ms)
            host_account_id = successor.account_id
            events.append(HostChanged(host=successor.pseudo))
        return self._changed(now_ms, *events, members=members, host_account_id=host_account_id)

    def close_for_inactivity(self, now_ms: int) -> Room:
        return self._changed(now_ms, RoomClosed(reason="inactive"), members=(), status="closed")

    # --- Mécanique ---

    def _team_for_newcomer(self, wanted: Optional[str]) -> str:
        if wanted is not None and self.team_choice_allowed:
            if wanted not in self.teams:
                raise RoomRuleError("Équipe inconnue.")
            if not self.has_room_in(wanted):
                raise RoomFullError("Cette équipe est complète.")
            return wanted
        # Sinon, l'équipe la moins nombreuse (la première à égalité) : des équipes équilibrées.
        return min((team for team in self.teams if self.has_room_in(team)), key=self.team_size)

    def _require_member(self, account_id: str) -> RoomMember:
        member = self.member(account_id)
        if member is None:
            raise RoomRuleError("Tu ne fais pas partie de ce salon.")
        return member

    def _changed(self, now_ms: int, *events: DomainEvent, **changes: object) -> Room:
        return replace(self, updated_at_ms=now_ms, pending_events=(*self.pending_events, *events), **changes)

    def pull_events(self) -> tuple[Room, tuple[DomainEvent, ...]]:
        return replace(self, pending_events=()), self.pending_events
