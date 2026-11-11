import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage, isAbort } from '../services/http';
import { PublicRoom, roomsApi } from '../services/roomsApi';

const REFRESH_MS = 10_000;

export type PublicRoomsState = { rooms: PublicRoom[] | null; error: string | null; refreshing: boolean };

/** Les parties publiques ouvertes, rafraîchies toutes les 10 s tant que la page est visible. */
export function usePublicRooms() {
  const [state, setState] = useState<PublicRoomsState>({ rooms: null, error: null, refreshing: true });
  const inFlight = useRef<AbortController | null>(null);

  const refresh = useCallback(() => {
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    setState((current) => ({ ...current, refreshing: true }));
    roomsApi
      .listPublic(controller.signal)
      .then((rooms) => setState({ rooms, error: null, refreshing: false }))
      .catch((error: unknown) => {
        if (!isAbort(error)) setState((current) => ({ ...current, error: errorMessage(error), refreshing: false }));
      });
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(() => document.visibilityState === 'visible' && refresh(), REFRESH_MS);
    const onVisible = () => document.visibilityState === 'visible' && refresh();
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      inFlight.current?.abort();
    };
  }, [refresh]);

  return { ...state, refresh };
}
