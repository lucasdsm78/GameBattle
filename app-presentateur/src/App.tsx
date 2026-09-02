import { useEffect, useState } from 'react';
import { DisplayBoard } from './components/DisplayBoard';
import { SpotifyDock } from './components/SpotifyDock';
import { GameConfigSocket } from './services/realtime/gameConfigSocket';
import { useGameConfigStore } from './store/gameConfigStore';
import { useSpotifyWebPlayback } from './hooks/useSpotifyWebPlayback';
import { useSpotifyBlindtestController } from './hooks/useSpotifyBlindtestController';
import {
  beginSpotifyLogin,
  completeSpotifyLogin,
  getValidSpotifyAccessToken,
  hasStoredSpotifyToken,
  isSpotifyConfigured,
  logoutSpotify,
} from './services/spotify/spotifyAuth';

const socket = new GameConfigSocket();

export default function App() {
  const { gameConfig, connectionState, errorMessage, setConnectionState, setErrorMessage, setGameConfig } =
    useGameConfigStore();
  const [spotifyConnected, setSpotifyConnected] = useState<boolean>(hasStoredSpotifyToken());

  // Handle the OAuth redirect (/callback?code=...) once on mount.
  useEffect(() => {
    if (window.location.pathname !== '/callback') {
      return;
    }
    completeSpotifyLogin()
      .then((ok) => {
        if (ok) {
          setSpotifyConnected(true);
        }
      })
      .catch((error: unknown) => {
        setErrorMessage(error instanceof Error ? error.message : 'Connexion Spotify échouée.');
      })
      .finally(() => {
        window.history.replaceState({}, '', '/');
      });
  }, [setErrorMessage]);

  useEffect(() => {
    socket.connect({
      onStatusChange: setConnectionState,
      onError: setErrorMessage,
      onMessage: (message) => {
        if (message.payload) {
          setGameConfig(message.payload);
        }
        if (message.type === 'error' && message.detail) {
          setErrorMessage(message.detail);
        }
      },
    });

    return () => socket.disconnect();
  }, [setConnectionState, setErrorMessage, setGameConfig]);

  // Pousse le token utilisateur Spotify vers le backend (pour l'import de playlist) dès qu'on est
  // connecté à Spotify ET au WebSocket. Re-poussé sur reconnexion WS, au retour sur l'onglet, et
  // toutes les 60 s pour que le backend ait toujours un token frais (getValidSpotifyAccessToken
  // rafraîchit automatiquement avant expiration).
  useEffect(() => {
    if (!spotifyConnected || connectionState !== 'connected') {
      return;
    }
    let cancelled = false;
    const push = async () => {
      const token = await getValidSpotifyAccessToken();
      if (token && !cancelled) {
        socket.sendSpotifyToken(token);
      }
    };
    push();
    const intervalId = window.setInterval(push, 60 * 1000);
    const onVisible = () => {
      if (document.visibilityState === 'visible') {
        push();
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    window.addEventListener('focus', onVisible);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('focus', onVisible);
    };
  }, [spotifyConnected, connectionState]);

  const { deviceId, status: playbackStatus, errorMessage: playbackError } = useSpotifyWebPlayback(spotifyConnected);

  useSpotifyBlindtestController({
    blindtest: gameConfig?.session.blindtest,
    deviceId,
    onError: setErrorMessage,
  });

  const handleConnect = () => {
    beginSpotifyLogin().catch((error: unknown) => {
      setErrorMessage(error instanceof Error ? error.message : 'Connexion Spotify impossible.');
    });
  };

  const handleLogout = () => {
    logoutSpotify();
    setSpotifyConnected(false);
  };

  return (
    <>
      <SpotifyDock
        configured={isSpotifyConfigured()}
        connected={spotifyConnected}
        status={playbackStatus}
        errorMessage={playbackError}
        onConnect={handleConnect}
        onLogout={handleLogout}
      />
      <DisplayBoard
        gameConfig={gameConfig}
        connectionState={connectionState}
        errorMessage={errorMessage}
        onBuzz={(team) => socket.buzz(team)}
        onStartChrono={() => socket.startChrono()}
        onStopChrono={() => socket.stopChrono()}
        onCultureBuzz={(team) => socket.cultureBuzz(team)}
        onBombeBuzz={(team) => socket.bombeBuzzer(team)}
        onBombeBeginAfterRoll={() => socket.beginBombeAfterRoll()}
        onBombeExplode={() => socket.explodeBombe()}
        onSevenDifferencesOpen={() => socket.openSevenDifferences()}
        onSevenDifferencesBuzz={(team) => socket.sevenDifferencesBuzzer(team)}
      />
    </>
  );
}
