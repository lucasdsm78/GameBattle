import { BlindtestAudioProvider } from '../services/audio/audioProviders';
import { useBlindtestAudioPlayer } from './useBlindtestAudioPlayer';
import { BlindtestState } from '../types/gameConfig';

type Options = {
  blindtest: BlindtestState | null | undefined;
  onSyncPlayback: (payload: {
    track_id: string;
    playback_state: 'stopped' | 'playing' | 'paused';
    position_ms: number;
    duration_ms: number;
  }) => void;
  onError: (message: string) => void;
  disabled?: boolean;
};

export function usePreviewAudioProvider({ blindtest, onSyncPlayback, onError, disabled = false }: Options): BlindtestAudioProvider {
  const preview = useBlindtestAudioPlayer({
    blindtest,
    onSyncPlayback,
    onError,
    disabled,
  });

  return {
    providerKind: 'preview',
    providerLabel: 'Preview native intégrée',
    isConfigured: true,
    isAuthenticating: false,
    canControlPlayback: preview.hasPreview && !disabled,
    hasPreview: preview.hasPreview,
    isBusy: preview.isLoading,
    isAuthenticated: false,
    requiresSpotifyPremium: false,
    supportsNativeSdk: false,
    positionMs: preview.positionMs,
    durationMs: preview.durationMs,
    progressRatio: preview.progressRatio,
    devices: [],
    selectedDeviceId: null,
    selectedDeviceName: null,
    controls: {
      login: async () => undefined,
      logout: async () => undefined,
      refreshDevices: async () => undefined,
      setSelectedDeviceId: () => undefined,
      playTrack: async () => undefined,
      pause: async () => undefined,
      resume: async () => undefined,
      stop: async () => undefined,
      seek: async () => undefined,
    },
  };
}


