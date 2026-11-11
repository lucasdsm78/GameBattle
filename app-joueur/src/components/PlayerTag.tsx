import { RoomPlayer } from '../services/roomsApi';

/** Un joueur du salon : pastille de présence, pseudo, hôte et « toi ». */
export function PlayerTag({ player }: { player: RoomPlayer }) {
  return (
    <span className={`player-tag${player.is_me ? ' is-me' : ''}`}>
      <span className={`presence${player.online ? ' is-online' : ''}`} aria-hidden="true" />
      <span className="player-pseudo">{player.pseudo}</span>
      <span className="sr-only">{player.online ? ' (en ligne)' : ' (hors ligne)'}</span>
      {player.is_host ? <span className="player-badge is-host">Hôte</span> : null}
      {player.is_me ? <span className="player-badge">Toi</span> : null}
    </span>
  );
}
