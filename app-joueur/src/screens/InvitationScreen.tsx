import { useCallback, useEffect, useState } from 'react';
import { Choice, ChoiceGroup } from '../components/ChoiceGroup';
import { RoomState } from '../hooks/useRoom';
import { ApiError, errorMessage, isAbort } from '../services/http';
import { VISIBILITY_LABELS, formatLabel, playersLabel, teamTone } from '../services/roomLabels';
import { INVITATION_CODE, Invitation, InvitationTeam, Room, roomsApi } from '../services/roomsApi';

type Props = {
  code: string;
  roomState: RoomState;
  onJoined: (room: Room) => void;
  onLeaveCurrent: () => Promise<void>;
  onDone: () => void;
};

type Preview = { status: 'loading' } | { status: 'failed'; message: string } | { status: 'ready'; invitation: Invitation };

const INVALID_LINK = 'Ce lien d’invitation n’est pas valide : vérifie qu’il est complet.';

/** L'équipe proposée d'office : la moins remplie parmi celles qui ont de la place (comme le ferait le serveur). */
const suggestedTeam = (teams: InvitationTeam[]) =>
  teams.filter((team) => !team.is_full).sort((a, b) => a.players.length - b.players.length)[0]?.name ?? '';

function teamChoices(teams: InvitationTeam[]): Choice<string>[] {
  return teams.map((team) => ({
    value: team.name,
    tone: teamTone(team.name),
    disabled: team.is_full,
    label: (
      <>
        {team.name}
        <span className="team-count">{team.is_full ? 'Complète' : `${team.players.length}/${team.capacity}`}</span>
      </>
    ),
    hint: team.players.length ? team.players.join(', ') : 'Personne pour l’instant',
  }));
}

/** Arrivée par un lien `/join/<code>` : aperçu de la partie, choix de l'équipe si elle est privée, puis entrée. */
export function InvitationScreen({ code, roomState, onJoined, onLeaveCurrent, onDone }: Props) {
  const [preview, setPreview] = useState<Preview>(() => (INVITATION_CODE.test(code) ? { status: 'loading' } : { status: 'failed', message: INVALID_LINK }));
  const [team, setTeam] = useState('');
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (signal?: AbortSignal) => {
      if (!INVITATION_CODE.test(code)) return;
      roomsApi
        .invitation(code, signal)
        .then((invitation) => {
          setPreview({ status: 'ready', invitation });
          setTeam((current) => (invitation.teams.some((t) => t.name === current && !t.is_full) ? current : suggestedTeam(invitation.teams)));
        })
        .catch((caught: unknown) => {
          if (!isAbort(caught)) setPreview({ status: 'failed', message: errorMessage(caught) });
        });
    },
    [code],
  );

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const invitation = preview.status === 'ready' ? preview.invitation : null;
  // Déjà dans ce salon (lien rouvert, double clic) : direction la salle d'attente.
  useEffect(() => {
    if (invitation?.already_member) onDone();
  }, [invitation, onDone]);

  async function join({ leaveCurrent = false } = {}) {
    setJoining(true);
    setError(null);
    try {
      if (leaveCurrent) await onLeaveCurrent();
      onJoined(await roomsApi.joinByInvitation(code, invitation?.can_choose_team ? team : undefined));
    } catch (caught) {
      setError(errorMessage(caught));
      setJoining(false);
      if (caught instanceof ApiError && caught.status === 409) load(); // complet ou équipe prise entre-temps : on montre l'état réel
    }
  }

  if (preview.status === 'failed') {
    return (
      <section className="panel status-card" role="alert">
        <h2 className="status-title">Invitation introuvable</h2>
        <p className="welcome-text">{preview.message}</p>
        <button type="button" className="primary-button" onClick={onDone}>
          Retour à l’accueil
        </button>
      </section>
    );
  }
  if (!invitation || roomState.status === 'loading' || invitation.already_member) {
    return (
      <section className="panel status-card is-loading" aria-busy="true" aria-label="Chargement de l’invitation">
        <span className="loader" />
      </section>
    );
  }

  const elsewhere = roomState.status === 'in-room';
  const closed = invitation.status !== 'lobby';
  const blocked = closed || invitation.is_full;

  return (
    <section className="panel lobby" aria-labelledby="invitation-title">
      <header className="lobby-head">
        <p className="eyebrow">Invitation</p>
        <h2 id="invitation-title" className="lobby-title">
          Partie de <span>{invitation.host}</span>
        </h2>
        <ul className="lobby-tags">
          <li>{VISIBILITY_LABELS[invitation.visibility]}</li>
          <li>{formatLabel(invitation.format, invitation.teams.length)}</li>
          <li>{playersLabel(invitation.player_count, invitation.capacity)}</li>
        </ul>
      </header>

      {blocked ? (
        <p className="notice" role="status">
          {closed ? 'Cette partie a déjà commencé.' : 'Cette partie est complète.'}
        </p>
      ) : invitation.can_choose_team ? (
        <ChoiceGroup legend="Choisis ton équipe" choices={teamChoices(invitation.teams)} value={team} onChange={setTeam} disabled={joining} />
      ) : (
        <p className="welcome-text">
          {invitation.format === 'solo' ? `Chacun pour soi, jusqu’à ${invitation.capacity} joueurs : chacun joue pour sa peau.` : 'Les équipes sont équilibrées automatiquement à ton arrivée.'}
        </p>
      )}

      {elsewhere && !blocked ? (
        <p className="notice" role="status">
          Tu es déjà dans un autre salon : rejoindre celui-ci t’en fera sortir.
        </p>
      ) : null}

      <p className="form-error" role="alert">
        {error}
      </p>

      <footer className="lobby-actions">
        {blocked ? null : (
          <button type="button" className="primary-button" onClick={() => join({ leaveCurrent: elsewhere })} disabled={joining || (invitation.can_choose_team && !team)} aria-busy={joining}>
            {joining ? 'Entrée…' : invitation.can_choose_team && team ? `Rejoindre les ${team}` : 'Rejoindre la partie'}
          </button>
        )}
        <button type="button" className="secondary-button" onClick={onDone} disabled={joining}>
          {elsewhere ? 'Retour à mon salon' : 'Retour à l’accueil'}
        </button>
      </footer>
    </section>
  );
}
