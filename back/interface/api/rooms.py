from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Body, Depends, Path, Request, Response, status

from application.rooms.commands.change_team import ChangeTeamCommand
from application.rooms.commands.create_room import CreateRoomCommand
from application.rooms.commands.join_room import JoinRoomCommand
from application.rooms.invitation_codes import CODE_ALPHABET, CODE_LENGTH
from interface.client_address import client_address
from interface.dependencies import CurrentPlayerDep, RoomCommandUseCaseDep, RoomQueryUseCaseDep
from interface.http_session import require_same_origin

router = APIRouter(prefix="/api/rooms", tags=["rooms"], dependencies=[Depends(require_same_origin)])

InvitationCode = Annotated[str, Path(pattern=f"^[{CODE_ALPHABET}]{{{CODE_LENGTH}}}$", description="Code du lien d'invitation")]
RoomId = Annotated[str, Path(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]
OptionalJoin = Annotated[Optional[JoinRoomCommand], Body()]


@router.post("", status_code=status.HTTP_201_CREATED, summary="Créer une partie (publique ou privée, chacun pour soi ou en équipes)")
async def create_room(command: CreateRoomCommand, player: CurrentPlayerDep, rooms: RoomCommandUseCaseDep) -> dict[str, Any]:
    return await rooms.create(player, command)


@router.get("/current", summary="La partie du joueur connecté, s'il en a une")
async def current_room(player: CurrentPlayerDep, rooms: RoomQueryUseCaseDep) -> dict[str, Any]:
    return {"room": await rooms.current(player)}


@router.get("/public", summary="Les parties publiques qui attendent des joueurs")
async def public_rooms(player: CurrentPlayerDep, rooms: RoomQueryUseCaseDep) -> dict[str, Any]:
    return {"rooms": await rooms.list_public()}


@router.get("/invitations/{code}", summary="Aperçu d'une partie avant de la rejoindre par son lien")
async def invitation(code: InvitationCode, request: Request, player: CurrentPlayerDep, rooms: RoomQueryUseCaseDep) -> dict[str, Any]:
    return await rooms.preview_invitation(player, code, client_address(request))


@router.post("/invitations/{code}/join", summary="Rejoindre par le lien (équipe au choix dans une partie privée)")
async def join_by_invitation(
    code: InvitationCode, request: Request, player: CurrentPlayerDep, rooms: RoomCommandUseCaseDep, command: OptionalJoin = None
) -> dict[str, Any]:
    return await rooms.join_by_invitation(player, code, command or JoinRoomCommand(), client_address(request))


@router.post("/{room_id}/join", summary="Rejoindre une partie publique")
async def join_public(room_id: RoomId, player: CurrentPlayerDep, rooms: RoomCommandUseCaseDep) -> dict[str, Any]:
    return await rooms.join_public(player, room_id)


@router.post("/current/team", summary="Changer d'équipe (partie privée en équipes)")
async def change_team(command: ChangeTeamCommand, player: CurrentPlayerDep, rooms: RoomCommandUseCaseDep) -> dict[str, Any]:
    return await rooms.change_team(player, command)


@router.post("/current/leave", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, summary="Quitter sa partie")
async def leave_room(player: CurrentPlayerDep, rooms: RoomCommandUseCaseDep) -> Response:
    await rooms.leave(player)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
