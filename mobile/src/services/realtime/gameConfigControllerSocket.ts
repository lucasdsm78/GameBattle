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

type PendingLaunch = {
  enabledGamesSignature: string;
  resolve: (snapshot: GameConfigSnapshot) => void;
  reject: (error: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
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
  private pendingLaunch: PendingLaunch | null = null;

  private rejectPendingLaunch(message: string): void {
    if (!this.pendingLaunch) return;
    clearTimeout(this.pendingLaunch.timeout);
    this.pendingLaunch.reject(new Error(message));
    this.pendingLaunch = null;
  }

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
          const enabledGamesSignature = message.payload.games
            .filter((game) => game.enabled)
            .map((game) => game.game_key)
            .sort()
            .join(',');
          if (
            this.pendingLaunch
            && message.payload.status === 'live'
            && message.payload.session.active_round
            && enabledGamesSignature === this.pendingLaunch.enabledGamesSignature
          ) {
            const pending = this.pendingLaunch;
            clearTimeout(pending.timeout);
            this.pendingLaunch = null;
            pending.resolve(message.payload);
          }
        }
        if (message.type === 'error' && message.detail) {
          handlers.onError(message.detail);
          this.rejectPendingLaunch(message.detail);
        }
      } catch {
        handlers.onError('Réponse WebSocket invalide.');
      }
    };
    this.socket.onerror = () => handlers.onError('Connexion WebSocket indisponible.');
    this.socket.onclose = (event) => {
      handlers.onStatusChange('disconnected');
      this.rejectPendingLaunch('Connexion au backend interrompue pendant le lancement.');
      if (event.code === 1008) {
        handlers.onError('Connexion refusée : vérifie le jeton contrôleur du mobile.');
      } else if (event.code !== 1000) {
        handlers.onError(`Connexion au backend interrompue (code ${event.code || 'réseau'}).`);
      }
      if (this.shouldReconnect) {
        this.reconnectTimer = setTimeout(() => {
          this.reconnectTimer = null;
          this.connect(handlers);
        }, 2000);
      }
    };
  }

  replaceConfig(config: GameDraft): void {
    this.sendMessage({ type: 'game.config.replace', payload: config });
  }

  validateAndLaunch(config: GameDraft): Promise<GameConfigSnapshot> {
    if (this.socket?.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error('Le backend n’est pas connecté. Réessaie dans quelques secondes.'));
    }
    this.rejectPendingLaunch('Une nouvelle demande de lancement remplace la précédente.');
    const enabledGamesSignature = config.games
      .filter((game) => game.enabled)
      .map((game) => game.game_key)
      .sort()
      .join(',');

    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        if (this.pendingLaunch?.reject !== reject) return;
        this.pendingLaunch = null;
        reject(new Error('Le lancement prend trop de temps. Vérifie la connexion puis réessaie.'));
      }, 10_000);
      this.pendingLaunch = { enabledGamesSignature, resolve, reject, timeout };
      this.socket?.send(JSON.stringify({
        type: 'game.config.validate-and-launch',
        payload: { ...config, rounds: [] },
      }));
    });
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

  startChrono(): void {
    this.sendMessage({ type: 'stopchrono.start' });
  }

  stopChrono(): void {
    this.sendMessage({ type: 'stopchrono.stop' });
  }

  nextChronoTeam(): void {
    this.sendMessage({ type: 'stopchrono.next-team' });
  }

  startCulture(): void {
    this.sendMessage({ type: 'culture.start' });
  }

  selectCultureDifficulty(difficulty: 'toutes' | 'facile' | 'moyen' | 'difficile'): void {
    this.sendMessage({ type: 'culture.select-difficulty', payload: { difficulty } });
  }

  cultureBuzzer(team: string): void {
    this.sendMessage({ type: 'culture.buzzer', payload: { team } });
  }

  cultureAnswer(isCorrect: boolean): void {
    this.sendMessage({ type: 'culture.answer', payload: { is_correct: isCorrect } });
  }

  nextCultureQuestion(): void {
    this.sendMessage({ type: 'culture.next-question' });
  }

  startBombe(): void {
    this.sendMessage({ type: 'bombe.start' });
  }

  bombeBuzzer(team: string): void {
    this.sendMessage({ type: 'bombe.buzzer', payload: { team } });
  }

  previousBombeTeam(): void {
    this.sendMessage({ type: 'bombe.previous-team' });
  }

  nextManche(): void {
    this.sendMessage({ type: 'game.next-manche' });
  }

  revealNextRanking(): void {
    this.sendMessage({ type: 'ranking.reveal-next' });
  }

  disconnect(): void {
    this.shouldReconnect = false;
    this.rejectPendingLaunch('Connexion fermée pendant le lancement.');
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.closeSocket();
  }
}


