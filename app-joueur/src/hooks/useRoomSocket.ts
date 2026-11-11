import { useEffect, useRef } from 'react';
import { Room, isRoom } from '../services/roomsApi';

/** État du lien temps réel, affiché dans la salle d'attente. `elsewhere` : un onglet plus récent a pris le relais. */
export type Link = 'connecting' | 'live' | 'reconnecting' | 'elsewhere';
export type Departure = 'left' | 'closed' | 'missing';

export type RoomSocketHandlers = {
  onRoom: (room: Room) => void;
  onLink: (link: Link) => void;
  onDeparture: (reason: Departure) => void;
  onSessionLost: () => void;
};

// Codes de fermeture du serveur (voir `interface/api/room_realtime.py`) : ceux-là ne se règlent pas en se reconnectant.
const CLOSE_NOT_MEMBER = 4000; // plus membre du salon, ou connexion remplacée par un onglet plus récent
const CLOSE_UNAUTHENTICATED = 4401;
const CLOSE_NOT_IN_ROOM = 4404;
const BACKOFF_BASE_MS = 500;
const BACKOFF_MAX_MS = 10_000;

const socketUrl = () => `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/rooms/current`;

/** Attente avant la n-ième reconnexion : exponentielle plafonnée, avec une part aléatoire pour ne pas revenir tous en même temps. */
const backoff = (attempt: number) => Math.min(BACKOFF_MAX_MS, BACKOFF_BASE_MS * 2 ** attempt) * (0.5 + Math.random() / 2);

function parse(data: unknown): { type?: unknown; room?: unknown } | null {
  if (typeof data !== 'string') return null;
  try {
    const message: unknown = JSON.parse(data);
    return typeof message === 'object' && message !== null ? message : null;
  } catch {
    return null;
  }
}

/**
 * Flux temps réel du salon : l'état complet arrive à chaque connexion puis à chaque changement (le client remplace
 * son état, rien à recoller). Ping du serveur → pong ; coupure réseau → reconnexion avec attente croissante,
 * aussitôt que la page redevient visible ou que le réseau revient. `session` force une nouvelle connexion.
 */
export function useRoomSocket(roomId: string | null, session: number, handlers: RoomSocketHandlers) {
  const latest = useRef(handlers);
  latest.current = handlers;

  useEffect(() => {
    if (!roomId) return;
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let attempt = 0;
    let stopped = false;
    let departed = false;

    const connect = () => {
      window.clearTimeout(retryTimer);
      retryTimer = undefined;
      if (stopped || socket) return;
      latest.current.onLink(attempt === 0 ? 'connecting' : 'reconnecting');
      const current = new WebSocket(socketUrl());
      socket = current;
      current.onmessage = (event) => {
        const message = parse(event.data);
        switch (message?.type) {
          case 'ping':
            current.send('{"type":"pong"}');
            break;
          case 'room.snapshot':
          case 'room.updated':
            if (isRoom(message.room)) {
              attempt = 0;
              latest.current.onLink('live');
              latest.current.onRoom(message.room);
            }
            break;
          case 'room.left':
          case 'room.closed':
            departed = true;
            latest.current.onDeparture(message.type === 'room.left' ? 'left' : 'closed');
            break;
        }
      };
      current.onclose = (event) => {
        if (socket === current) socket = null;
        if (stopped || departed) return;
        if (event.code === CLOSE_UNAUTHENTICATED) latest.current.onSessionLost();
        else if (event.code === CLOSE_NOT_IN_ROOM) latest.current.onDeparture('missing');
        else if (event.code === CLOSE_NOT_MEMBER) latest.current.onLink('elsewhere');
        else {
          latest.current.onLink('reconnecting');
          retryTimer = window.setTimeout(connect, backoff(attempt++));
        }
      };
    };

    // Retour sur la page ou du réseau : on n'attend pas la fin du délai en cours.
    const resumeNow = () => {
      if (retryTimer !== undefined && document.visibilityState === 'visible' && navigator.onLine) connect();
    };
    window.addEventListener('online', resumeNow);
    document.addEventListener('visibilitychange', resumeNow);
    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      window.removeEventListener('online', resumeNow);
      document.removeEventListener('visibilitychange', resumeNow);
      socket?.close(1000);
    };
  }, [roomId, session]);
}
