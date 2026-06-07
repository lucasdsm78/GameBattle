import { useEffect, useRef, useState } from 'react';
import { getValidSpotifyAccessToken } from '../services/spotify/spotifyAuth';

const SDK_SRC = 'https://sdk.scdn.co/spotify-player.js';
const PLAYER_NAME = 'GameBattle Écran';

export type WebPlaybackStatus = 'idle' | 'loading' | 'ready' | 'not-ready' | 'error';

type UseSpotifyWebPlaybackResult = {
  deviceId: string | null;
  status: WebPlaybackStatus;
  errorMessage: string | null;
};

let sdkScriptPromise: Promise<void> | null = null;

const loadSdkScript = (): Promise<void> => {
  if (window.Spotify) {
    return Promise.resolve();
  }
  if (sdkScriptPromise) {
    return sdkScriptPromise;
  }
  sdkScriptPromise = new Promise<void>((resolve, reject) => {
    window.onSpotifyWebPlaybackSDKReady = () => resolve();
    const script = document.createElement('script');
    script.src = SDK_SRC;
    script.async = true;
    script.onerror = () => reject(new Error('Impossible de charger le SDK Spotify.'));
    document.body.appendChild(script);
  });
  return sdkScriptPromise;
};

// Boots the Web Playback SDK once `enabled` is true (i.e. user is connected).
// Registers a "GameBattle Écran" device and returns its id once ready.
export function useSpotifyWebPlayback(enabled: boolean): UseSpotifyWebPlaybackResult {
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [status, setStatus] = useState<WebPlaybackStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const playerRef = useRef<SpotifyPlayer | null>(null);

  useEffect(() => {
    if (!enabled || playerRef.current) {
      return;
    }

    let cancelled = false;
    setStatus('loading');

    loadSdkScript()
      .then(() => {
        if (cancelled || !window.Spotify) {
          return;
        }
        const player = new window.Spotify.Player({
          name: PLAYER_NAME,
          volume: 0.8,
          getOAuthToken: (cb) => {
            getValidSpotifyAccessToken().then((token) => {
              if (token) {
                cb(token);
              }
            });
          },
        });
        playerRef.current = player;

        const setError = (message: string) => {
          if (cancelled) {
            return;
          }
          setErrorMessage(message);
          setStatus('error');
        };

        player.addListener('ready', ({ device_id }) => {
          if (!cancelled) {
            setDeviceId(device_id);
            setStatus('ready');
          }
        });
        player.addListener('not_ready', () => {
          if (!cancelled) {
            setDeviceId(null);
            setStatus('not-ready');
          }
        });
        player.addListener('initialization_error', ({ message }) => setError(message));
        player.addListener('authentication_error', ({ message }) => setError(message));
        player.addListener('account_error', () =>
          setError('Compte Spotify Premium requis pour la lecture sur l’écran.'),
        );
        player.addListener('playback_error', ({ message }) => setError(message));

        player.connect();
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : 'Erreur SDK Spotify.');
          setStatus('error');
        }
      });

    return () => {
      cancelled = true;
      playerRef.current?.disconnect();
      playerRef.current = null;
    };
  }, [enabled]);

  return { deviceId, status, errorMessage };
}
