import { Room } from '../services/roomsApi';
import { freeSeatsLabel, teamTone } from '../services/roomLabels';
import { PlayerTag } from './PlayerTag';

type Props = { room: Room; switching: string | null; onPick: (team: string) => void };

/** Les équipes côte à côte, places libres comprises. Dans une partie privée, on change d'équipe d'un geste. */
export function TeamBoard({ room, switching, onPick }: Props) {
  return (
    <ul className="team-board" aria-label="Équipes">
      {room.teams.map((team) => {
        const players = room.players.filter((player) => player.team === team.name);
        const mine = room.me?.team === team.name;
        const full = players.length >= team.capacity;
        return (
          <li key={team.name} className={`team-card ${teamTone(team.name)}${mine ? ' is-mine' : ''}`}>
            <h3 className="team-name">
              {team.name}
              <span className="team-count">
                {players.length}/{team.capacity}
              </span>
            </h3>
            <ul className="team-slots">
              {players.map((player) => (
                <li key={player.pseudo}>
                  <PlayerTag player={player} />
                </li>
              ))}
              {full ? null : (
                <li className="free-slot">{freeSeatsLabel(team.capacity - players.length)}</li>
              )}
            </ul>
            {room.can_choose_team && !mine ? (
              <button
                type="button"
                className="team-join"
                onClick={() => onPick(team.name)}
                disabled={full || switching !== null}
                aria-busy={switching === team.name}
              >
                {full ? 'Complète' : switching === team.name ? 'Changement…' : `Passer chez les ${team.name}`}
              </button>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
