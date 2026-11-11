import { FormEvent, useState } from 'react';
import { usePublicRooms } from '../hooks/usePublicRooms';
import { errorMessage } from '../services/http';
import { formatLabel, playersLabel } from '../services/roomLabels';
import { Room, invitationCodeFrom, roomsApi } from '../services/roomsApi';
import { Field, helpId } from './Field';

type Props = { onJoined: (room: Room) => void; onInvitation: (code: string) => void };

export function JoinRoomCard({ onJoined, onInvitation }: Props) {
  const publicRooms = usePublicRooms();
  const [code, setCode] = useState('');
  const [codeError, setCodeError] = useState<string | null>(null);
  const [joining, setJoining] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = invitationCodeFrom(code);
    if (parsed) onInvitation(parsed);
    else setCodeError(code.trim() ? 'Ce lien ou ce code n’est pas valide : vérifie qu’il est complet.' : 'Colle le lien ou le code reçu.');
  }

  async function join(roomId: string) {
    setJoining(roomId);
    setError(null);
    try {
      onJoined(await roomsApi.joinPublic(roomId));
    } catch (caught) {
      setError(errorMessage(caught));
      setJoining(null);
      publicRooms.refresh();
    }
  }

  return (
    <section className="panel play-card" aria-labelledby="join-title">
      <h2 id="join-title" className="section-title">
        Rejoindre une partie
      </h2>
      <form className="code-form" onSubmit={onSubmit} noValidate>
        <Field id="invitation-code" label="Lien ou code d’invitation" error={codeError} hint="Le lien reçu d’un ami, ou son code à 10 caractères.">
          <div className="invite-row">
            <input
              id="invitation-code"
              className="field-input"
              value={code}
              onChange={(event) => {
                setCode(event.target.value);
                setCodeError(null);
              }}
              autoComplete="off"
              autoCapitalize="characters"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="go"
              maxLength={300}
              aria-invalid={codeError ? true : undefined}
              aria-describedby={helpId('invitation-code')}
            />
            <button type="submit" className="tool-button">
              Ouvrir
            </button>
          </div>
        </Field>
      </form>

      <div className="public-head">
        <h3 className="field-label">Parties publiques</h3>
        <button type="button" className="link-button" onClick={publicRooms.refresh} disabled={publicRooms.refreshing}>
          {publicRooms.refreshing ? 'Actualisation…' : 'Actualiser'}
        </button>
      </div>
      <p className="form-error" role="alert">
        {error ?? publicRooms.error}
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
              <button type="button" className="tool-button" onClick={() => join(room.id)} disabled={joining !== null} aria-busy={joining === room.id}>
                {joining === room.id ? 'Entrée…' : 'Rejoindre'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
