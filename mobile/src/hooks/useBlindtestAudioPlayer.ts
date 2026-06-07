import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Audio, AVPlaybackStatus } from 'expo-av';
import { BlindtestState } from '../types/gameConfig';

type SyncPayload = {
  track_id: string;
  playback_state: 'stopped' | 'playing' | 'paused';
  position_ms: number;
  duration_ms: number;
};

type Options = {
  blindtest: BlindtestState | null | undefined;
  onSyncPlayback: (payload: SyncPayload) => void;
  onError: (message: string) => void;
  disabled?: boolean;
};

type PlayerUiState = {
  isReady: boolean;
  isLoading: boolean;
  hasPreview: boolean;
  playbackState: 'stopped' | 'playing' | 'paused';
  positionMs: number;
  durationMs: number;
};

const SYNC_INTERVAL_MS = 1000;
const POSITION_DRIFT_MS = 1200;

const normalizePosition = (positionMs: number, durationMs: number) => {
  if (durationMs <= 0) {
    return Math.max(positionMs, 0);
  }
  return Math.min(Math.max(positionMs, 0), durationMs);
};

export function useBlindtestAudioPlayer({ blindtest, onSyncPlayback, onError, disabled = false }: Options) {
  const soundRef = useRef<Audio.Sound | null>(null);
  const activeTrackIdRef = useRef('');
  const lastSyncedAtRef = useRef(0);
  const [uiState, setUiState] = useState<PlayerUiState>({
    isReady: false,
    isLoading: false,
    hasPreview: false,
    playbackState: 'stopped',
    positionMs: 0,
    durationMs: 0,
  });

  const emitSync = useCallback(
    (payload: SyncPayload, force = false) => {
      const now = Date.now();
      if (!force && now - lastSyncedAtRef.current < SYNC_INTERVAL_MS) {
        return;
      }
      lastSyncedAtRef.current = now;
      onSyncPlayback(payload);
    },
    [onSyncPlayback],
  );

  const unloadSound = useCallback(async () => {
    const current = soundRef.current;
    soundRef.current = null;
    activeTrackIdRef.current = '';
    if (current) {
      try {
        await current.unloadAsync();
      } catch {
        // ignore cleanup errors
      }
    }
    setUiState((state) => ({
      ...state,
      isReady: false,
      isLoading: false,
      hasPreview: false,
      playbackState: 'stopped',
      positionMs: 0,
      durationMs: 0,
    }));
  }, []);

  const handlePlaybackStatus = useCallback(
    (status: AVPlaybackStatus) => {
      if (!status.isLoaded) {
        if ('error' in status && status.error) {
          onError(`Lecture audio impossible : ${status.error}`);
        }
        return;
      }

      const nextState: SyncPayload['playback_state'] = status.isPlaying
        ? 'playing'
        : status.didJustFinish
          ? 'stopped'
        : status.positionMillis > 0
          ? 'paused'
          : 'stopped';

      setUiState({
        isReady: true,
        isLoading: false,
        hasPreview: true,
        playbackState: nextState,
        positionMs: status.positionMillis,
        durationMs: status.durationMillis ?? 0,
      });

      if (blindtest?.current_track?.track_id) {
        emitSync(
          {
            track_id: blindtest.current_track.track_id,
            playback_state: nextState,
            position_ms: status.positionMillis,
            duration_ms: status.durationMillis ?? 0,
          },
          status.didJustFinish,
        );
      }
    },
    [blindtest?.current_track?.track_id, emitSync, onError],
  );

  useEffect(() => {
    Audio.setAudioModeAsync({
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
      shouldDuckAndroid: true,
    }).catch(() => {
      onError("Impossible d'initialiser l'audio mobile.");
    });
  }, [onError]);

  useEffect(() => {
    if (disabled) {
      unloadSound().catch(() => undefined);
      return;
    }

    const activeTrack = blindtest?.current_track;
    const nextTrackId = activeTrack?.track_id ?? '';
    const previewUrl = activeTrack?.preview_url?.trim() ?? '';

    if (!nextTrackId || !previewUrl) {
      unloadSound().catch(() => undefined);
      if (activeTrack && !previewUrl) {
        setUiState((state) => ({ ...state, hasPreview: false, isReady: false, isLoading: false }));
      }
      return;
    }

    if (activeTrackIdRef.current === nextTrackId) {
      return;
    }

    let cancelled = false;
    const load = async () => {
      setUiState((state) => ({ ...state, isLoading: true, hasPreview: true }));
      await unloadSound();

      const sound = new Audio.Sound();
      soundRef.current = sound;
      activeTrackIdRef.current = nextTrackId;

      try {
        await sound.loadAsync(
          { uri: previewUrl },
          {
            shouldPlay: blindtest?.playback_state === 'playing',
            positionMillis: blindtest?.playback_position_ms ?? 0,
            progressUpdateIntervalMillis: 500,
          },
          false,
        );
        sound.setOnPlaybackStatusUpdate(handlePlaybackStatus);
        if (!cancelled) {
          const status = await sound.getStatusAsync();
          handlePlaybackStatus(status);
        }
      } catch {
        onError("Impossible de charger la preview audio de cette musique.");
        await unloadSound();
      }
    };

    load().catch(() => onError("Erreur inattendue lors du chargement audio."));

    return () => {
      cancelled = true;
    };
  }, [blindtest?.current_track, blindtest?.playback_position_ms, blindtest?.playback_state, disabled, handlePlaybackStatus, onError, unloadSound]);

  useEffect(() => {
    if (disabled) {
      return;
    }

    const sound = soundRef.current;
    if (!sound || !blindtest?.current_track) {
      return;
    }

    const syncRemoteState = async () => {
      const status = await sound.getStatusAsync();
      if (!status.isLoaded) {
        return;
      }

      const desiredState = blindtest.playback_state;
      const desiredPosition = normalizePosition(blindtest.playback_position_ms, status.durationMillis ?? 0);
      const positionDrift = Math.abs((status.positionMillis ?? 0) - desiredPosition);

      if (positionDrift > POSITION_DRIFT_MS) {
        await sound.setPositionAsync(desiredPosition);
      }

      if (desiredState === 'playing' && !status.isPlaying) {
        await sound.playAsync();
      }
      if (desiredState === 'paused' && status.isPlaying) {
        await sound.pauseAsync();
      }
      if (desiredState === 'stopped') {
        await sound.stopAsync();
      }
    };

    syncRemoteState().catch(() => {
      onError("Impossible de synchroniser la lecture audio avec le backend.");
    });
  }, [blindtest?.current_track?.track_id, blindtest?.playback_position_ms, blindtest?.playback_state, disabled, onError]);

  useEffect(() => {
    return () => {
      unloadSound().catch(() => undefined);
    };
  }, [unloadSound]);

  const progressRatio = useMemo(() => {
    if (uiState.durationMs <= 0) {
      return 0;
    }
    return Math.min(uiState.positionMs / uiState.durationMs, 1);
  }, [uiState.durationMs, uiState.positionMs]);

  return {
    ...uiState,
    progressRatio,
  };
}




