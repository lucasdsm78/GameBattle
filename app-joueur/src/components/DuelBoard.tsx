import { Room } from '../services/roomsApi';
import { PlayerTag } from './PlayerTag';

/** 1 contre 1 : toi à gauche, ton adversaire (ou son arrivée) à droite. */
export function DuelBoard({ room }: { room: Room }) {
  const me = room.players.find((player) => player.is_me);
  const opponent = room.players.find((player) => !player.is_me);
  return (
    <div className="duel" aria-label="Face-à-face">
      <div className="duel-side tone-blue">{me ? <PlayerTag player={me} /> : null}</div>
      <span className="duel-versus" aria-hidden="true">
        VS
      </span>
      <div className="duel-side tone-red">
        {opponent ? (
          <PlayerTag player={opponent} />
        ) : (
          <span className="waiting">
            En attente d’un adversaire<span className="dots" aria-hidden="true" />
          </span>
        )}
      </div>
    </div>
  );
}
