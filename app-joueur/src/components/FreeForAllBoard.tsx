import { freeSeatsLabel, playerTone } from '../services/roomLabels';
import { Room } from '../services/roomsApi';
import { PlayerTag } from './PlayerTag';

/** Chacun pour soi : un pupitre par joueur, dans l'ordre d'arrivée, puis les places encore libres. */
export function FreeForAllBoard({ room }: { room: Room }) {
  const free = room.capacity - room.player_count;
  return (
    <ul className="ffa-board" aria-label="Joueurs">
      {room.players.map((player, index) => (
        <li key={player.pseudo} className={`ffa-seat ${playerTone(index)}${player.is_me ? ' is-mine' : ''}`}>
          <PlayerTag player={player} />
        </li>
      ))}
      {free > 0 ? <li className="free-slot ffa-free">{freeSeatsLabel(free)}</li> : null}
    </ul>
  );
}
