import { usePublicRooms } from '../hooks/usePublicRooms';
import { formatLabel, playersLabel } from '../services/roomLabels';

type Props = { joining: string | null; onJoin: (roomId: string) => void };

/** Les parties publiques qui attendent des joueurs, pour en choisir une précise (celle d'un ami, un format…). */
export function PublicRoomList({ joining, onJoin }: Props) {
  const publicRooms = usePublicRooms(true);
  return (
    <div className="public-rooms">
      <div className="public-head">
        <h3 className="field-label">Parties publiques</h3>
        <button type="button" className="link-button" onClick={publicRooms.refresh} disabled={publicRooms.refreshing}>
          {publicRooms.refreshing ? 'Actualisation…' : 'Actualiser'}
        </button>
      </div>
      <p className="form-error" role="alert">
        {publicRooms.error}
      </p>
      {publicRooms.rooms === null ? (
        <span className="loader is-small" aria-label="Chargement des parties" />
      ) : publicRooms.rooms.length === 0 ? (
        <p className="empty-state">Aucune partie publique pour l’instant. Crée la tienne !</p>
      ) : (
        <ul className="public-list">
          {publicRooms.rooms.map((room) => (
            <li key={room.id} className="public-room">
              <span className="public-room-info">
                <b>Partie de {room.host}</b>
                <span>
                  {formatLabel(room.format, room.team_count)} · {playersLabel(room.player_count, room.capacity)}
                </span>
              </span>
              <button type="button" className="tool-button" onClick={() => onJoin(room.id)} disabled={joining !== null} aria-busy={joining === room.id}>
                {joining === room.id ? 'Entrée…' : 'Rejoindre'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
