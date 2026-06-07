// Minimal type declarations for the Spotify Web Playback SDK
// (subset used by GameBattle — avoids an extra @types dependency)

interface SpotifyPlayerInit {
  name: string;
  getOAuthToken: (cb: (token: string) => void) => void;
  volume?: number;
}

interface SpotifyPlayerError {
  message: string;
}

interface SpotifyReadyEvent {
  device_id: string;
}

interface SpotifyPlayer {
  connect(): Promise<boolean>;
  disconnect(): void;
  addListener(event: 'ready' | 'not_ready', cb: (event: SpotifyReadyEvent) => void): boolean;
  addListener(
    event: 'initialization_error' | 'authentication_error' | 'account_error' | 'playback_error',
    cb: (event: SpotifyPlayerError) => void,
  ): boolean;
  removeListener(event: string): boolean;
  setVolume(volume: number): Promise<void>;
}

interface SpotifyNamespace {
  Player: new (init: SpotifyPlayerInit) => SpotifyPlayer;
}

interface Window {
  Spotify?: SpotifyNamespace;
  onSpotifyWebPlaybackSDKReady?: () => void;
}
