import { GameConfigMessage } from '../../types/gameConfig';

type Handlers = {
  onMessage: (message: GameConfigMessage) => void;
  onStatusChange: (status: 'connecting' | 'connected' | 'disconnected') => void;
  onError: (message: string) => void;
};

const buildUrl = (): string => {
  const base = (import.meta.env.VITE_GAMEBATTLE_WS_URL as string | undefined) ?? 'ws://localhost:8000';
  const token = (import.meta.env.VITE_GAMEBATTLE_DISPLAY_TOKEN as string | undefined) ?? 'change-me-display';
  const normalized = base.replace(/\/$/, '');
  return `${normalized}/ws/game-config?client_type=display&token=${encodeURIComponent(token)}`;
};

export class GameConfigSocket {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private handlers: Handlers | null = null;
  private shouldReconnect = true;

  private closeSocket(): void {
    if (this.socket) {
      this.socket.onopen = null;
      this.socket.onmessage = null;
      this.socket.onerror = null;
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
  }

  private sendMessage(message: Record<string, unknown>): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  connect(handlers: Handlers): void {
    this.handlers = handlers;
    this.shouldReconnect = true;
    handlers.onStatusChange('connecting');

    this.closeSocket();
    this.socket = new WebSocket(buildUrl());

    this.socket.onopen = () => handlers.onStatusChange('connected');
    this.socket.onmessage = (event) => {
      try {
        handlers.onMessage(JSON.parse(event.data) as GameConfigMessage);
      } catch {
        handlers.onError('Message WebSocket invalide.');
      }
    };
    this.socket.onerror = () => handlers.onError('Connexion WebSocket indisponible.');
    this.socket.onclose = () => {
      handlers.onStatusChange('disconnected');
      if (this.shouldReconnect) {
        this.reconnectTimer = window.setTimeout(() => this.connect(handlers), 2000);
      }
    };
  }

  buzz(team: string): void {
    this.sendMessage({ type: 'blindtest.buzzer', payload: { team } });
  }

  // Pousse le token utilisateur Spotify vers le backend pour autoriser l'import de playlist.
  sendSpotifyToken(accessToken: string): void {
    this.sendMessage({ type: 'spotify.user-token', payload: { access_token: accessToken } });
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.closeSocket();
  }
}
