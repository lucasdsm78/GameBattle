import { useEffect, useRef } from 'react';
import { BlindtestState } from '../types/gameConfig';
import { getValidSpotifyAccessToken } from '../services/spotify/spotifyAuth';

const API_BASE = 'https://api.spotify.com/v1';

type Options = {
  blindtest: BlindtestState | null | undefined;
  deviceId: string | null;
  onError: (message: string) => void;
};

const spotifyFetch = async (path: string, init: RequestInit): Promise<void> => {
  const token = await getValidSpotifyAccessToken();
  if (!token) {
    throw new Error('Session Spotify expirée. Reconnecte-toi.');
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });
  // 204 = success (no content). 404 = device not found yet (ignored, will retry on next state).
  if (!response.ok && response.status !== 404) {
    throw new Error(`Spotify a refusé la commande de lecture (${response.status}).`);
  }
};

// Mirrors the backend blindtest playback state onto the Web Playback SDK device:
//  - new track + "playing"  -> start the track from 0 on our device
//  - "paused"               -> pause
//  - "playing" (same track) -> resume
//  - "stopped"              -> pause
export function useSpotifyBlindtestController({ blindtest, deviceId, onError }: Options): void {
  const lastTrackIdRef = useRef<string>('');
  const lastStateRef = useRef<BlindtestState['playback_state']>('stopped');

  const trackId = blindtest?.current_track?.track_id ?? '';
  const playbackState = blindtest?.playback_state ?? 'stopped';

  useEffect(() => {
    if (!deviceId || !trackId) {
      return;
    }

    const playTrack = () =>
      spotifyFetch(`/me/player/play?device_id=${deviceId}`, {
        method: 'PUT',
        body: JSON.stringify({ uris: [`spotify:track:${trackId}`], position_ms: 0 }),
      });
    const resume = () => spotifyFetch(`/me/player/play?device_id=${deviceId}`, { method: 'PUT' });
    const pause = () => spotifyFetch(`/me/player/pause?device_id=${deviceId}`, { method: 'PUT' });

    const apply = async () => {
      const trackChanged = trackId !== lastTrackIdRef.current;

      if (trackChanged) {
        lastTrackIdRef.current = trackId;
        lastStateRef.current = playbackState;
        if (playbackState === 'playing') {
          await playTrack();
        }
        return;
      }

      if (playbackState === lastStateRef.current) {
        return;
      }
      lastStateRef.current = playbackState;
      if (playbackState === 'playing') {
        await resume();
      } else {
        await pause();
      }
    };

    apply().catch((error: unknown) => {
      onError(error instanceof Error ? error.message : 'Erreur de lecture Spotify.');
    });
  }, [deviceId, trackId, playbackState, onError]);
}
