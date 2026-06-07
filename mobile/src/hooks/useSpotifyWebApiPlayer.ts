import { useAuthRequest, ResponseType, exchangeCodeAsync } from 'expo-auth-session';
import * as WebBrowser from 'expo-web-browser';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BlindtestState, BlindtestTrack } from '../types/gameConfig';
import {
  buildSpotifyRedirectUri,
  getSpotifyAuthConfig,
  loadSpotifyTokenSet,
  normalizeSpotifyTokenResponse,
  refreshSpotifyTokenSet,
  spotifyDiscovery,
  SpotifyTokenSet,
  storeSpotifyTokenSet,
} from '../services/audio/spotifyAuth';

WebBrowser.maybeCompleteAuthSession();

const SPOTIFY_SCOPES = [
  'user-read-playback-state',
  'user-modify-playback-state',
  'user-read-currently-playing',
  'streaming',
];

const TOKEN_REFRESH_WINDOW_MS = 60_000;
const POLL_INTERVAL_MS = 2_500;

type SpotifyPlaybackDevice = {
  id: string;
  is_active: boolean;
  is_restricted: boolean;
  name: string;
  type: string;
  volume_percent: number | null;
};

type PlaybackSyncPayload = {
  track_id: string;
  playback_state: 'stopped' | 'playing' | 'paused';
  position_ms: number;
  duration_ms: number;
};

type Options = {
  blindtest: BlindtestState | null | undefined;
  onSyncPlayback: (payload: PlaybackSyncPayload) => void;
  onError: (message: string) => void;
};

const isTokenExpired = (tokenSet: SpotifyTokenSet): boolean => Date.now() >= tokenSet.expiresAt - TOKEN_REFRESH_WINDOW_MS;

const trackUri = (trackId: string): string => `spotify:track:${trackId}`;

export function useSpotifyWebApiPlayer({ blindtest, onSyncPlayback, onError }: Options) {
  const config = useMemo(() => getSpotifyAuthConfig(), []);
  const redirectUri = useMemo(() => buildSpotifyRedirectUri(), []);
  const [tokenSet, setTokenSet] = useState<SpotifyTokenSet | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [devices, setDevices] = useState<SpotifyPlaybackDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const lastAppliedSignatureRef = useRef('');
  const lastSyncedSignatureRef = useRef('');

  const [request, , promptAsync] = useAuthRequest(
    {
      clientId: config.clientId || 'missing-spotify-client-id',
      scopes: SPOTIFY_SCOPES,
      responseType: ResponseType.Code,
      usePKCE: true,
      redirectUri,
      extraParams: {
        show_dialog: 'true',
      },
    },
    spotifyDiscovery,
  );

  const persistTokenSet = useCallback(async (nextTokenSet: SpotifyTokenSet | null) => {
    setTokenSet(nextTokenSet);
    await storeSpotifyTokenSet(nextTokenSet);
  }, []);

  const ensureValidToken = useCallback(async (): Promise<string> => {
    if (!tokenSet) {
      throw new Error('Connecte un compte Spotify Premium pour utiliser la lecture complète.');
    }

    if (!isTokenExpired(tokenSet)) {
      return tokenSet.accessToken;
    }

    const refreshed = await refreshSpotifyTokenSet(tokenSet);
    await persistTokenSet(refreshed);
    return refreshed.accessToken;
  }, [persistTokenSet, tokenSet]);

  const spotifyApiRequest = useCallback(
    async <T>(path: string, init: RequestInit = {}, allowEmpty = false): Promise<T | null> => {
      const accessToken = await ensureValidToken();
      const response = await fetch(`https://api.spotify.com/v1${path}`, {
        ...init,
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
          ...(init.headers ?? {}),
        },
      });

      if (response.status === 204) {
        return null;
      }

      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || `Spotify a répondu ${response.status}.`);
      }

      if (allowEmpty) {
        return null;
      }
      return (await response.json()) as T;
    },
    [ensureValidToken],
  );

  const refreshDevices = useCallback(async () => {
    if (!tokenSet) {
      setDevices([]);
      setSelectedDeviceId(null);
      return [] as SpotifyPlaybackDevice[];
    }

    const payload = await spotifyApiRequest<{ devices: SpotifyPlaybackDevice[] }>('/me/player/devices');
    const nextDevices = payload?.devices ?? [];
    setDevices(nextDevices);
    setSelectedDeviceId((current) => {
      if (current && nextDevices.some((device) => device.id === current)) {
        return current;
      }
      return nextDevices.find((device) => device.is_active)?.id ?? nextDevices[0]?.id ?? null;
    });
    return nextDevices;
  }, [spotifyApiRequest, tokenSet]);

  const ensureDeviceId = useCallback(async (): Promise<string> => {
    const nextDevices = devices.length ? devices : await refreshDevices();
    const deviceId = selectedDeviceId ?? nextDevices.find((device) => device.is_active)?.id ?? nextDevices[0]?.id;
    if (!deviceId) {
      throw new Error('Aucun appareil Spotify actif. Ouvre Spotify sur le téléphone ou un appareil Connect.');
    }
    return deviceId;
  }, [devices, refreshDevices, selectedDeviceId]);

  const transferPlaybackToDevice = useCallback(
    async (deviceId: string) => {
      await spotifyApiRequest('/me/player', {
        method: 'PUT',
        body: JSON.stringify({ device_ids: [deviceId], play: false }),
      }, true);
    },
    [spotifyApiRequest],
  );

  const playTrack = useCallback(
    async (track: BlindtestTrack, positionMs = 0) => {
      const deviceId = await ensureDeviceId();
      await transferPlaybackToDevice(deviceId);
      await spotifyApiRequest(
        `/me/player/play?device_id=${encodeURIComponent(deviceId)}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            uris: [trackUri(track.track_id)],
            position_ms: Math.max(positionMs, 0),
          }),
        },
        true,
      );
    },
    [ensureDeviceId, spotifyApiRequest, transferPlaybackToDevice],
  );

  const resume = useCallback(async () => {
    const deviceId = await ensureDeviceId();
    await spotifyApiRequest(`/me/player/play?device_id=${encodeURIComponent(deviceId)}`, { method: 'PUT' }, true);
  }, [ensureDeviceId, spotifyApiRequest]);

  const pause = useCallback(async () => {
    const deviceId = await ensureDeviceId();
    await spotifyApiRequest(`/me/player/pause?device_id=${encodeURIComponent(deviceId)}`, { method: 'PUT' }, true);
  }, [ensureDeviceId, spotifyApiRequest]);

  const seek = useCallback(
    async (positionMs: number) => {
      const deviceId = await ensureDeviceId();
      await spotifyApiRequest(
        `/me/player/seek?device_id=${encodeURIComponent(deviceId)}&position_ms=${Math.max(positionMs, 0)}`,
        { method: 'PUT' },
        true,
      );
    },
    [ensureDeviceId, spotifyApiRequest],
  );

  const stop = useCallback(async () => {
    await pause();
    await seek(0);
  }, [pause, seek]);

  const login = useCallback(async () => {
    if (!config.isConfigured) {
      onError('Configure expo.extra.spotifyClientId pour activer Spotify Premium.');
      return;
    }
    if (!request) {
      onError('La demande d’authentification Spotify est en cours d’initialisation.');
      return;
    }

    setIsAuthenticating(true);
    try {
      const result = await promptAsync();
      if (result.type !== 'success' || !('code' in result.params)) {
        return;
      }

      const exchanged = await exchangeCodeAsync(
        {
          clientId: config.clientId,
          code: result.params.code,
          redirectUri,
          extraParams: {
            code_verifier: request.codeVerifier ?? '',
          },
        },
        spotifyDiscovery,
      );
      const normalized = normalizeSpotifyTokenResponse(exchanged);
      await persistTokenSet(normalized);
      await refreshDevices();
    } catch {
      onError('Connexion Spotify impossible. Vérifie le client ID, le redirect URI et ton abonnement Premium.');
    } finally {
      setIsAuthenticating(false);
    }
  }, [config.clientId, config.isConfigured, onError, persistTokenSet, promptAsync, redirectUri, refreshDevices, request]);

  const logout = useCallback(async () => {
    await persistTokenSet(null);
    setDevices([]);
    setSelectedDeviceId(null);
  }, [persistTokenSet]);

  useEffect(() => {
    const bootstrap = async () => {
      const stored = await loadSpotifyTokenSet();
      if (!stored) {
        return;
      }
      try {
        const nextTokenSet = isTokenExpired(stored) ? await refreshSpotifyTokenSet(stored) : stored;
        await persistTokenSet(nextTokenSet);
      } catch {
        await persistTokenSet(null);
      }
    };

    bootstrap().catch(() => {
      onError('Impossible de restaurer la session Spotify.');
    });
  }, [onError, persistTokenSet]);

  useEffect(() => {
    if (!tokenSet) {
      return;
    }
    refreshDevices().catch(() => {
      onError('Impossible de récupérer les appareils Spotify disponibles.');
    });
  }, [onError, refreshDevices, tokenSet]);

  useEffect(() => {
    if (!tokenSet) {
      return;
    }

    const interval = setInterval(() => {
      spotifyApiRequest<{
        device?: { id: string };
        is_playing?: boolean;
        progress_ms?: number;
        item?: { id?: string; duration_ms?: number };
      }>('/me/player')
        .then((payload) => {
          if (!payload?.item?.id || !blindtest?.current_track?.track_id) {
            return;
          }
          if (payload.item.id !== blindtest.current_track.track_id) {
            return;
          }
          const nextState: PlaybackSyncPayload['playback_state'] = payload.is_playing ? 'playing' : 'paused';
          const signature = `${payload.item.id}:${nextState}:${payload.progress_ms ?? 0}:${payload.item.duration_ms ?? 0}`;
          if (lastSyncedSignatureRef.current === signature) {
            return;
          }
          lastSyncedSignatureRef.current = signature;
          onSyncPlayback({
            track_id: payload.item.id,
            playback_state: nextState,
            position_ms: payload.progress_ms ?? 0,
            duration_ms: payload.item.duration_ms ?? 0,
          });
          if (payload.device?.id) {
            setSelectedDeviceId(payload.device.id);
          }
        })
        .catch(() => undefined);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [blindtest?.current_track?.track_id, onSyncPlayback, spotifyApiRequest, tokenSet]);

  useEffect(() => {
    const activeTrack = blindtest?.current_track;
    if (!tokenSet || !blindtest || !activeTrack?.track_id || !selectedDeviceId) {
      return;
    }

    const activeBlindtest = blindtest;

    const applyRemotePlayback = async () => {
      const signature = `${activeTrack.track_id}:${activeBlindtest.playback_state}:${activeBlindtest.playback_position_ms}:${selectedDeviceId}`;
      if (lastAppliedSignatureRef.current === signature) {
        return;
      }
      lastAppliedSignatureRef.current = signature;

      if (activeBlindtest.playback_state === 'playing') {
        await playTrack(activeTrack, activeBlindtest.playback_position_ms);
        return;
      }
      if (activeBlindtest.playback_state === 'paused') {
        await seek(activeBlindtest.playback_position_ms);
        await pause();
        return;
      }
      await stop();
    };

    applyRemotePlayback().catch(() => {
      onError('Impossible de piloter Spotify. Vérifie qu’un appareil Spotify Premium est actif.');
    });
  }, [blindtest?.current_track, blindtest?.playback_position_ms, blindtest?.playback_state, onError, pause, playTrack, seek, selectedDeviceId, stop, tokenSet]);

  const deviceOptions = useMemo(
    () => devices.filter((device) => !device.is_restricted),
    [devices],
  );

  const selectedDevice = useMemo(
    () => deviceOptions.find((device) => device.id === selectedDeviceId) ?? null,
    [deviceOptions, selectedDeviceId],
  );

  const canControlPlayback = Boolean(tokenSet && selectedDeviceId);

  return {
    isConfigured: config.isConfigured,
    isAuthenticated: Boolean(tokenSet),
    isAuthenticating,
    isBusy,
    redirectUri,
    devices: deviceOptions,
    selectedDeviceId,
    selectedDevice,
    canControlPlayback,
    setSelectedDeviceId,
    refreshDevices: async () => {
      setIsBusy(true);
      try {
        await refreshDevices();
      } finally {
        setIsBusy(false);
      }
    },
    login,
    logout,
    playTrack: async (track: BlindtestTrack, positionMs = 0) => {
      setIsBusy(true);
      try {
        await playTrack(track, positionMs);
      } finally {
        setIsBusy(false);
      }
    },
    pause: async () => {
      setIsBusy(true);
      try {
        await pause();
      } finally {
        setIsBusy(false);
      }
    },
    resume: async () => {
      setIsBusy(true);
      try {
        await resume();
      } finally {
        setIsBusy(false);
      }
    },
    stop: async () => {
      setIsBusy(true);
      try {
        await stop();
      } finally {
        setIsBusy(false);
      }
    },
    seek: async (positionMs: number) => {
      setIsBusy(true);
      try {
        await seek(positionMs);
      } finally {
        setIsBusy(false);
      }
    },
  };
}


