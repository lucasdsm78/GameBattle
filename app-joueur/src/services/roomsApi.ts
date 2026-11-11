import { ApiError, isObject, postJson, readJson, send } from './http';

export type Visibility = 'public' | 'private';
export type RoomFormat = 'solo' | 'teams';

export type RoomPlayer = { pseudo: string; team: string; is_host: boolean; is_me: boolean; online: boolean };
export type RoomTeam = { name: string; capacity: number };

/** Le salon tel que le voit le joueur connecté (jamais d'identifiant de compte : les joueurs se reconnaissent au pseudo). */
export type Room = {
  id: string;
  visibility: Visibility;
  format: RoomFormat;
  status: string;
  invite_path: string;
  host: string;
  player_count: number;
  capacity: number;
  teams: RoomTeam[];
  players: RoomPlayer[];
  can_choose_team: boolean;
  me: { pseudo: string; team: string; is_host: boolean } | null;
  version: number;
};

export type PublicRoom = { id: string; host: string; format: RoomFormat; team_count: number; player_count: number; capacity: number };

export type InvitationTeam = { name: string; capacity: number; players: string[]; is_full: boolean };
export type Invitation = {
  visibility: Visibility;
  format: RoomFormat;
  status: string;
  host: string;
  player_count: number;
  capacity: number;
  is_full: boolean;
  can_choose_team: boolean;
  already_member: boolean;
  teams: InvitationTeam[];
};

export type CreateRoom = { visibility: Visibility; format: RoomFormat; team_count: number };

const BASE_URL = '/api/rooms';
// Même alphabet et même longueur que le serveur : un lien mal copié est refusé sans requête.
export const INVITATION_CODE = /^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{10}$/;

// Contrôles de forme volontairement légers : le serveur est de la même origine, on vérifie juste qu'on parle du bon objet.
export const isRoom = (body: unknown): body is Room =>
  isObject(body) && typeof body.id === 'string' && typeof body.invite_path === 'string' && Array.isArray(body.players) && Array.isArray(body.teams);
const isCurrent = (body: unknown): body is { room: Room | null } => isObject(body) && (body.room === null || isRoom(body.room));
const isPublicList = (body: unknown): body is { rooms: PublicRoom[] } => isObject(body) && Array.isArray(body.rooms);
const isInvitation = (body: unknown): body is Invitation => isObject(body) && typeof body.host === 'string' && Array.isArray(body.teams);

const readRoom = (response: Response) => readJson(response, isRoom);

/** Le code d'un lien d'invitation collé tel quel (`https://…/join/ABC…`), ou le code seul ; `null` s'il est illisible. */
export function invitationCodeFrom(input: string): string | null {
  const trimmed = input.trim();
  const candidate = (trimmed.match(/\/join\/([^/?#\s]+)/i)?.[1] ?? trimmed).toUpperCase();
  return INVITATION_CODE.test(candidate) ? candidate : null;
}

export const invitationUrl = (room: Room) => new URL(room.invite_path, window.location.origin).toString();

export const roomsApi = {
  current: (signal?: AbortSignal) =>
    send(`${BASE_URL}/current`, { signal })
      .then((response) => readJson(response, isCurrent))
      .then((body) => body.room),
  listPublic: (signal?: AbortSignal) =>
    send(`${BASE_URL}/public`, { signal })
      .then((response) => readJson(response, isPublicList))
      .then((body) => body.rooms),
  create: (settings: CreateRoom) => postJson(BASE_URL, settings).then(readRoom),
  invitation: (code: string, signal?: AbortSignal) => send(`${BASE_URL}/invitations/${code}`, { signal }).then((response) => readJson(response, isInvitation)),
  joinByInvitation: (code: string, team?: string) => postJson(`${BASE_URL}/invitations/${code}/join`, team ? { team } : undefined).then(readRoom),
  joinPublic: (roomId: string) => postJson(`${BASE_URL}/${encodeURIComponent(roomId)}/join`).then(readRoom),
  changeTeam: (team: string) => postJson(`${BASE_URL}/current/team`, { team }).then(readRoom),
  leave: async (): Promise<void> => {
    await postJson(`${BASE_URL}/current/leave`);
  },
};

export const isNotSignedIn = (error: unknown) => error instanceof ApiError && error.status === 401;
