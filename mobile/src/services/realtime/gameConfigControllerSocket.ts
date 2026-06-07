import Constants from 'expo-constants';
import {
  BlindtestPlaylistSeedTrack,
  GameConfigMessage,
  GameConfigSnapshot,
  GameDraft,
} from '../../types/gameConfig';

type Handlers = {
  onSnapshot: (config: GameConfigSnapshot) => void;
  onStatusChange: (status: 'connecting' | 'connected' | 'disconnected') => void;
  onError: (message: string) => void;
};

const extra = (Constants.expoConfig?.extra ?? {}) as {
  backendWsUrl?: string;
  controllerToken?: string;
};

const socketUrl = (): string => {
  const base = (extra.backendWsUrl ?? 'ws://localhost:8000').replace(/\/$/, '');
  const token = extra.controllerToken ?? 'change-me-controller';
  return `${base}/ws/game-config?client_type=controller&token=${encodeURIComponent(token)}`;
};

export class GameConfigControllerSocket {
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
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
    this.socket = new WebSocket(socketUrl());

    this.socket.onopen = () => handlers.onStatusChange('connected');
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as GameConfigMessage;
        if (message.payload) {
          handlers.onSnapshot(message.payload);
        }
        if (message.type === 'error' && message.detail) {
          handlers.onError(message.detail);
        }
      } catch {
        handlers.onError('Réponse WebSocket invalide.');
      }
    };
    this.socket.onerror = () => handlers.onError('Connexion WebSocket indisponible.');
    this.socket.onclose = () => {
      handlers.onStatusChange('disconnected');
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this.connect(handlers), 2000);
      }
    };
  }

  replaceConfig(config: GameDraft): void {
    this.sendMessage({ type: 'game.config.replace', payload: config });
  }

  launchGame(): void {
    this.sendMessage({ type: 'game.config.launch' });
  }

  loadBlindtestPlaylist(tracks: BlindtestPlaylistSeedTrack[]): void {
    this.sendMessage({ type: 'blindtest.playlist.load', payload: { tracks } });
  }

  importSpotifyPlaylist(playlistUrl: string): void {
    this.sendMessage({ type: 'blindtest.playlist.import-spotify', payload: { playlist_url: playlistUrl } });
  }

  // Recharge la playlist fixe configurée côté serveur (GAMEBATTLE_BLINDTEST_PLAYLIST_URL).
  reloadPlaylist(): void {
    this.sendMessage({ type: 'blindtest.playlist.reload' });
  }

  buzz(team: string): void {
    this.sendMessage({ type: 'blindtest.buzzer', payload: { team } });
  }

  answer(isCorrect: boolean): void {
    this.sendMessage({ type: 'blindtest.answer', payload: { is_correct: isCorrect } });
  }

  controlPlayback(action: 'play' | 'pause' | 'resume' | 'stop' | 'seek', positionMs?: number): void {
    this.sendMessage({ type: 'blindtest.playback.control', payload: { action, position_ms: positionMs } });
  }

  syncPlayback(payload: {
    track_id: string;
    playback_state: 'stopped' | 'playing' | 'paused';
    position_ms: number;
    duration_ms: number;
  }): void {
    this.sendMessage({ type: 'blindtest.playback.sync', payload });
  }

  nextTrack(): void {
    this.sendMessage({ type: 'blindtest.next-track' });
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.closeSocket();
  }
}


