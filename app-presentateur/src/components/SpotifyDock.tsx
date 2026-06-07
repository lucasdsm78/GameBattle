import { WebPlaybackStatus } from '../hooks/useSpotifyWebPlayback';

type Props = {
  configured: boolean;
  connected: boolean;
  status: WebPlaybackStatus;
  errorMessage: string | null;
  onConnect: () => void;
  onLogout: () => void;
};

const STATUS_LABEL: Record<WebPlaybackStatus, string> = {
  idle: 'En veille',
  loading: 'Initialisation du lecteur…',
  ready: 'Lecteur prêt',
  'not-ready': 'Lecteur hors ligne',
  error: 'Erreur lecteur',
};

export function SpotifyDock({ configured, connected, status, errorMessage, onConnect, onLogout }: Props) {
  if (!configured) {
    return (
      <div className="spotify-dock spotify-dock--warning">
        <span className="spotify-dot" />
        <span>Spotify non configuré (VITE_SPOTIFY_CLIENT_ID)</span>
      </div>
    );
  }

  if (!connected) {
    return (
      <div className="spotify-dock">
        <button type="button" className="spotify-connect" onClick={onConnect}>
          Connecter Spotify
        </button>
      </div>
    );
  }

  return (
    <div className={`spotify-dock spotify-dock--${status}`}>
      <span className="spotify-dot" />
      <span className="spotify-status">{errorMessage ?? STATUS_LABEL[status]}</span>
      <button type="button" className="spotify-logout" onClick={onLogout}>
        Déconnecter
      </button>
    </div>
  );
}
