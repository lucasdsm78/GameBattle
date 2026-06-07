import { useSpotifyWebApiPlayer } from './useSpotifyWebApiPlayer';
import { BlindtestAudioProvider } from '../services/audio/audioProviders';
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
};

export function useSpotifyWebApiAudioProvider({ blindtest, onSyncPlayback, onError }: Options): BlindtestAudioProvider {
  const webApi = useSpotifyWebApiPlayer({ blindtest, onSyncPlayback, onError });

  return {
    providerKind: 'spotify-web-api',
    providerLabel: 'Spotify Web API',
    isConfigured: webApi.isConfigured,
    isAuthenticating: webApi.isAuthenticating,
    canControlPlayback: webApi.canControlPlayback,
    hasPreview: false,
    isBusy: webApi.isBusy,
    isAuthenticated: webApi.isAuthenticated,
    requiresSpotifyPremium: true,
    supportsNativeSdk: false,
    positionMs: blindtest?.playback_position_ms ?? 0,
    durationMs: blindtest?.playback_duration_ms ?? 0,
    progressRatio:
      (blindtest?.playback_duration_ms ?? 0) > 0
        ? Math.min((blindtest?.playback_position_ms ?? 0) / (blindtest?.playback_duration_ms ?? 1), 1)
        : 0,
    devices: webApi.devices.map((device) => ({
      id: device.id,
      name: device.name,
      type: device.type,
    })),
    selectedDeviceId: webApi.selectedDeviceId,
    selectedDeviceName: webApi.selectedDevice?.name ?? null,
    controls: {
      login: webApi.login,
      logout: webApi.logout,
      refreshDevices: webApi.refreshDevices,
      setSelectedDeviceId: webApi.setSelectedDeviceId,
      playTrack: webApi.playTrack,
      pause: webApi.pause,
      resume: webApi.resume,
      stop: webApi.stop,
      seek: webApi.seek,
    },
  };
}


