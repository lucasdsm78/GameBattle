import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BlindtestTrack, BlindtestState } from '../types/gameConfig';
import {
  BlindtestAudioProvider,
  BlindtestAudioProviderDevices,
  BlindtestPlaybackSyncPayload,
  noopAsync,
} from '../services/audio/audioProviders';
import {
  getSpotifySdkCapabilities,
  initializeSpotifySdkBridge,
  spotifySdkBridge,
} from '../services/audio/spotifySdkBridge';

type Options = {
  blindtest: BlindtestState | null | undefined;
  onSyncPlayback: (payload: BlindtestPlaybackSyncPayload) => void;
  onError: (message: string) => void;
};

const POLL_INTERVAL_MS = 1000;

const trackUriFromId = (trackId: string): string => `spotify:track:${trackId.trim()}`;

export function useSpotifySdkAudioProvider({ blindtest, onSyncPlayback, onError }: Options): BlindtestAudioProvider {
  const capabilities = useMemo(() => getSpotifySdkCapabilities(), []);
  const [isConnected, setIsConnected] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [positionMs, setPositionMs] = useState(0);
  const [durationMs, setDurationMs] = useState(0);
  const lastSyncedSignatureRef = useRef('');
  const lastAppliedSignatureRef = useRef('');

  const devices = useMemo<BlindtestAudioProviderDevices[]>(() => {
    if (!capabilities.available) {
      return [];
    }
    return [{ id: 'spotify-sdk-local-device', name: 'Spotify SDK local', type: 'sdk' }];
  }, [capabilities.available]);

  const selectedDeviceId = devices[0]?.id ?? null;
  const selectedDeviceName = devices[0]?.name ?? null;
  const progressRatio = durationMs > 0 ? Math.min(positionMs / durationMs, 1) : 0;

  const login = useCallback(async () => {
    if (!capabilities.isConfigured || !capabilities.available) {
      onError('Spotify SDK natif indisponible ou non configuré.');
      return;
    }
    setIsBusy(true);
    try {
      await initializeSpotifySdkBridge();
      await spotifySdkBridge.connect();
      setIsConnected(true);
    } catch {
      onError('Connexion au Spotify SDK natif impossible. Vérifie le client ID, le redirect URI et l’app Spotify installée.');
    } finally {
      setIsBusy(false);
    }
  }, [capabilities.available, capabilities.isConfigured, onError]);

  const logout = useCallback(async () => {
    setIsBusy(true);
    try {
      await spotifySdkBridge.disconnect();
      setIsConnected(false);
    } finally {
      setIsBusy(false);
    }
  }, []);

  const playTrack = useCallback(async (track: BlindtestTrack, seekPositionMs = 0) => {
    setIsBusy(true);
    try {
      await spotifySdkBridge.play(trackUriFromId(track.track_id), seekPositionMs);
      setIsConnected(true);
    } finally {
      setIsBusy(false);
    }
  }, []);

  const pause = useCallback(async () => {
    setIsBusy(true);
    try {
      await spotifySdkBridge.pause();
    } finally {
      setIsBusy(false);
    }
  }, []);

  const resume = useCallback(async () => {
    setIsBusy(true);
    try {
      await spotifySdkBridge.resume();
    } finally {
      setIsBusy(false);
    }
  }, []);

  const stop = useCallback(async () => {
    setIsBusy(true);
    try {
      await spotifySdkBridge.pause();
      await spotifySdkBridge.seek(0);
    } finally {
      setIsBusy(false);
    }
  }, []);

  const seek = useCallback(async (seekPositionMs: number) => {
    setIsBusy(true);
    try {
      await spotifySdkBridge.seek(seekPositionMs);
    } finally {
      setIsBusy(false);
    }
  }, []);

  useEffect(() => {
    const currentTrack = blindtest?.current_track;
    if (!isConnected || !currentTrack?.track_id) {
      return;
    }

    const interval = setInterval(() => {
      spotifySdkBridge
        .getPlayerState()
        .then((state) => {
          if (!state?.trackUri) {
            return;
          }
          const expectedTrackUri = trackUriFromId(currentTrack.track_id);
          if (state.trackUri !== expectedTrackUri) {
            return;
          }
          const nextState: BlindtestPlaybackSyncPayload['playback_state'] = state.isPaused ? 'paused' : 'playing';
          const signature = `${state.trackUri}:${nextState}:${state.playbackPosition}:${durationMs}`;
          if (lastSyncedSignatureRef.current === signature) {
            return;
          }
          lastSyncedSignatureRef.current = signature;
          setPositionMs(state.playbackPosition);
          onSyncPlayback({
            track_id: currentTrack.track_id,
            playback_state: nextState,
            position_ms: state.playbackPosition,
            duration_ms: durationMs,
          });
        })
        .catch(() => undefined);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [blindtest?.current_track, durationMs, isConnected, onSyncPlayback]);

  useEffect(() => {
    const activeTrack = blindtest?.current_track;
    if (!isConnected || !blindtest || !activeTrack?.track_id) {
      return;
    }

    const activeBlindtest = blindtest;

    const signature = `${activeTrack.track_id}:${activeBlindtest.playback_state}:${activeBlindtest.playback_position_ms}`;
    if (lastAppliedSignatureRef.current === signature) {
      return;
    }
    lastAppliedSignatureRef.current = signature;

    const apply = async () => {
      setDurationMs(activeBlindtest.playback_duration_ms);
      if (activeBlindtest.playback_state === 'playing') {
        await playTrack(activeTrack, activeBlindtest.playback_position_ms);
        return;
      }
      if (activeBlindtest.playback_state === 'paused') {
        await playTrack(activeTrack, activeBlindtest.playback_position_ms);
        await pause();
        return;
      }
      await stop();
    };

    apply().catch(() => {
      onError('Impossible de piloter le Spotify SDK natif.');
    });
  }, [blindtest?.current_track, blindtest?.playback_duration_ms, blindtest?.playback_position_ms, blindtest?.playback_state, isConnected, onError, pause, playTrack, stop]);

  return {
    providerKind: 'spotify-sdk',
    providerLabel: capabilities.available ? 'Spotify SDK natif' : 'Spotify SDK indisponible',
    isConfigured: capabilities.isConfigured,
    isAuthenticating: false,
    canControlPlayback: capabilities.available && capabilities.isConfigured && isConnected,
    hasPreview: false,
    isBusy,
    isAuthenticated: isConnected,
    requiresSpotifyPremium: true,
    supportsNativeSdk: true,
    positionMs,
    durationMs,
    progressRatio,
    devices,
    selectedDeviceId,
    selectedDeviceName,
    controls: {
      login,
      logout,
      refreshDevices: noopAsync,
      setSelectedDeviceId: () => undefined,
      playTrack,
      pause,
      resume,
      stop,
      seek,
    },
  };
}



