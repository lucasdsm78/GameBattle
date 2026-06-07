import { useMemo } from 'react';
import { BlindtestState } from '../types/gameConfig';
import { BlindtestAudioProvider } from '../services/audio/audioProviders';
import { resolveBlindtestAudioMode } from '../services/audio/spotifyPlayback';
import { usePreviewAudioProvider } from './usePreviewAudioProvider';
import { useSpotifySdkAudioProvider } from './useSpotifySdkAudioProvider';
import { useSpotifyWebApiAudioProvider } from './useSpotifyWebApiAudioProvider';

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

export function useBlindtestAudioProviders({ blindtest, onSyncPlayback, onError }: Options): {
  activeProvider: BlindtestAudioProvider;
  previewProvider: BlindtestAudioProvider;
  spotifySdkProvider: BlindtestAudioProvider;
  spotifyWebApiProvider: BlindtestAudioProvider;
} {
  const spotifySdkProvider = useSpotifySdkAudioProvider({ blindtest, onSyncPlayback, onError });
  const spotifyWebApiProvider = useSpotifyWebApiAudioProvider({ blindtest, onSyncPlayback, onError });

  const providerMode = useMemo(
    () =>
      resolveBlindtestAudioMode(blindtest?.current_track, {
        spotifyConnected: spotifySdkProvider.canControlPlayback || spotifyWebApiProvider.canControlPlayback,
      }),
    [blindtest?.current_track, spotifySdkProvider.canControlPlayback, spotifyWebApiProvider.canControlPlayback],
  );

  const activeProvider = useMemo<BlindtestAudioProvider>(() => {
    if (providerMode === 'spotify-full') {
      if (spotifySdkProvider.canControlPlayback || spotifySdkProvider.isAuthenticated) {
        return spotifySdkProvider;
      }
      return spotifyWebApiProvider;
    }
    return spotifyWebApiProvider;
  }, [providerMode, spotifySdkProvider, spotifyWebApiProvider]);

  const previewProvider = usePreviewAudioProvider({
    blindtest,
    onSyncPlayback,
    onError,
    disabled: providerMode === 'spotify-full',
  });

  return {
    activeProvider,
    previewProvider,
    spotifySdkProvider,
    spotifyWebApiProvider,
  };
}

