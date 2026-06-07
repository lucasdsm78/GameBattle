import { BlindtestTrack } from '../../types/gameConfig';

export type BlindtestPlaybackSyncPayload = {
  track_id: string;
  playback_state: 'stopped' | 'playing' | 'paused';
  position_ms: number;
  duration_ms: number;
};

export type BlindtestAudioProviderKind = 'preview' | 'spotify-web-api' | 'spotify-sdk' | 'spotify-app' | 'none';

export type BlindtestAudioProviderState = {
  providerKind: BlindtestAudioProviderKind;
  providerLabel: string;
  isConfigured: boolean;
  isAuthenticating: boolean;
  canControlPlayback: boolean;
  hasPreview: boolean;
  isBusy: boolean;
  isAuthenticated: boolean;
  requiresSpotifyPremium: boolean;
  supportsNativeSdk: boolean;
  positionMs: number;
  durationMs: number;
  progressRatio: number;
};

export type BlindtestAudioProviderDevices = {
  id: string;
  name: string;
  type: string;
};

export type BlindtestAudioProviderControls = {
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshDevices: () => Promise<void>;
  setSelectedDeviceId: (deviceId: string) => void;
  playTrack: (track: BlindtestTrack, positionMs?: number) => Promise<void>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  stop: () => Promise<void>;
  seek: (positionMs: number) => Promise<void>;
};

export type BlindtestAudioProvider = BlindtestAudioProviderState & {
  selectedDeviceId: string | null;
  selectedDeviceName: string | null;
  devices: BlindtestAudioProviderDevices[];
  controls: BlindtestAudioProviderControls;
};

export const noopAsync = async (): Promise<void> => undefined;


