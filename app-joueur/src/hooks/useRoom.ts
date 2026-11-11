import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, errorMessage, isAbort } from '../services/http';
import { Room, isNotSignedIn, roomsApi } from '../services/roomsApi';
import { Departure, Link, useRoomSocket } from './useRoomSocket';

export type RoomState =
  | { status: 'loading' }
  | { status: 'unreachable'; message: string }
  | { status: 'none'; notice?: string }
  | { status: 'in-room'; room: Room; link: Link };

const DEPARTURE_NOTICES: Record<Departure, string | undefined> = {
  left: 'Tu n’es plus dans ce salon.',
  closed: 'Le salon a été fermé.',
  missing: undefined,
};

/**
 * Une réponse HTTP ne connaît pas la présence (elle vient du temps réel) : on garde celle qu'on avait.
 * Une réponse plus ancienne que l'état affiché (version inférieure) est ignorée.
 */
function merge(previous: RoomState, next: Room, { fromSocket }: { fromSocket: boolean }): RoomState {
  if (previous.status !== 'in-room' || previous.room.id !== next.id) return { status: 'in-room', room: next, link: 'connecting' };
  if (next.version < previous.room.version) return previous;
  if (fromSocket) return { ...previous, room: next };
  const online = new Map(previous.room.players.map((player) => [player.pseudo, player.online]));
  const players = next.players.map((player) => ({ ...player, online: player.online || (online.get(player.pseudo) ?? false) }));
  return { ...previous, room: { ...next, players } };
}

/** Le salon du joueur : chargé une fois par HTTP, puis tenu à jour par le WebSocket du salon. */
export function useRoom(onSessionLost: () => void) {
  const [state, setState] = useState<RoomState>({ status: 'loading' });
  const [session, setSession] = useState(0);
  // Départ demandé ici : l'avis « tu n'es plus dans ce salon » serait de trop. Reste levé jusqu'à la prochaine entrée,
  // car l'annonce du serveur peut arriver après la réponse HTTP, avant que la connexion ne soit fermée.
  const leaving = useRef(false);

  const load = useCallback(
    (signal?: AbortSignal, notice?: string) => {
      setState((current) => (current.status === 'in-room' ? current : { status: 'loading' }));
      roomsApi
        .current(signal)
        .then((room) => setState((current) => (room ? merge(current, room, { fromSocket: false }) : { status: 'none', notice })))
        .catch((error: unknown) => {
          if (isAbort(error)) return;
          if (isNotSignedIn(error)) onSessionLost();
          else setState({ status: 'unreachable', message: errorMessage(error, 'Impossible de joindre le serveur.') });
        });
    },
    [onSessionLost],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const roomId = state.status === 'in-room' ? state.room.id : null;
  useRoomSocket(roomId, session, {
    onRoom: (room) => setState((current) => merge(current, room, { fromSocket: true })),
    onLink: (link) => setState((current) => (current.status === 'in-room' ? { ...current, link } : current)),
    onDeparture: (reason) => {
      if (reason === 'missing') load();
      else setState({ status: 'none', notice: leaving.current ? undefined : DEPARTURE_NOTICES[reason] });
    },
    onSessionLost,
  });

  /** Résultat d'une action HTTP (création, entrée, changement d'équipe) : affiché sans attendre le temps réel. */
  const entered = useCallback((room: Room) => {
    leaving.current = false;
    setState((current) => merge(current, room, { fromSocket: false }));
  }, []);
  /** Quitter. Déjà sorti (autre onglet, salon fermé entre-temps) : le résultat est le même. */
  const leave = useCallback(async () => {
    leaving.current = true;
    try {
      await roomsApi.leave();
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 404)) {
        leaving.current = false;
        throw error;
      }
    }
    setState({ status: 'none' });
  }, []);
  /** « Afficher ici » après qu'un autre onglet a pris le salon : nouvelle connexion, qui reprend la main à son tour. */
  const resume = useCallback(() => setSession((value) => value + 1), []);

  return { state, entered, leave, resume, reload: () => load() };
}
