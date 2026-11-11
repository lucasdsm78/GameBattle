import { useState } from 'react';
import { DuelBoard } from '../components/DuelBoard';
import { InviteLink } from '../components/InviteLink';
import { TeamBoard } from '../components/TeamBoard';
import { Link } from '../hooks/useRoomSocket';
import { errorMessage } from '../services/http';
import { VISIBILITY_LABELS, formatLabel, playersLabel } from '../services/roomLabels';
import { Room, roomsApi } from '../services/roomsApi';

type Props = {
  room: Room;
  link: Link;
  onRoom: (room: Room) => void;
  onLeave: () => Promise<void>;
  onResume: () => void;
};

const LINK_LABELS: Record<Link, string> = {
  connecting: 'Connexion…',
  live: 'En direct',
  reconnecting: 'Reconnexion…',
  elsewhere: 'Ouvert ailleurs',
};

/** Salle d'attente : qui est là, dans quelle équipe, et le lien pour inviter les autres. */
export function RoomLobby({ room, link, onRoom, onLeave, onResume }: Props) {
  const [switching, setSwitching] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isHost = room.me?.is_host ?? false;
  const waitingFor = room.capacity - room.player_count;

  async function pickTeam(team: string) {
    setSwitching(team);
    setError(null);
    try {
      onRoom(await roomsApi.changeTeam(team));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSwitching(null);
    }
  }

  async function leave() {
    setLeaving(true);
    setError(null);
    try {
      await onLeave();
    } catch (caught) {
      setError(errorMessage(caught, 'Impossible de quitter le salon. Réessaie.'));
      setLeaving(false);
    }
  }

  return (
    <section className="panel lobby" aria-labelledby="lobby-title">
      <header className="lobby-head">
        <p className="eyebrow">Salle d’attente</p>
        <h2 id="lobby-title" className="lobby-title">
          {formatLabel(room.format, room.teams.length)}
        </h2>
        <ul className="lobby-tags">
          <li>{VISIBILITY_LABELS[room.visibility]}</li>
          <li>{playersLabel(room.player_count, room.capacity)}</li>
          <li className={`link-state is-${link}`} role="status">
            {LINK_LABELS[link]}
          </li>
        </ul>
      </header>

      {link === 'elsewhere' ? (
        <div className="notice" role="alert">
          <p>Ce salon est ouvert dans un autre onglet ou sur un autre appareil.</p>
          <button type="button" className="tool-button" onClick={onResume}>
            Afficher ici
          </button>
        </div>
      ) : null}

      <InviteLink room={room} />

      {room.format === 'solo' ? <DuelBoard room={room} /> : <TeamBoard room={room} switching={switching} onPick={pickTeam} />}

      <p className="form-error" role="alert">
        {error}
      </p>

      <footer className="lobby-actions">
        <button type="button" className="primary-button" disabled aria-describedby="start-note">
          Lancer la partie
        </button>
        <p id="start-note" className="lobby-note">
          {isHost
            ? `Les jeux en ligne arrivent bientôt : tu lanceras la partie d’ici.${waitingFor > 0 ? ` Encore ${waitingFor} place${waitingFor > 1 ? 's' : ''} libre${waitingFor > 1 ? 's' : ''}.` : ''}`
            : `${room.host} lancera la partie dès que les jeux en ligne seront ouverts.`}
        </p>
        <button type="button" className="secondary-button" onClick={leave} disabled={leaving} aria-busy={leaving}>
          {leaving ? 'Départ…' : 'Quitter le salon'}
        </button>
      </footer>
    </section>
  );
}
