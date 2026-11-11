import { useEffect, useState } from 'react';
import { Room, invitationUrl } from '../services/roomsApi';

type Feedback = 'idle' | 'copied' | 'failed';

async function copy(text: string, field: HTMLInputElement | null): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Presse-papiers refusé (contexte non sécurisé, permission) : on sélectionne le lien pour une copie manuelle.
    field?.select();
    return false;
  }
}

/** Le lien d'invitation, à copier ou partager (feuille de partage native sur téléphone). */
export function InviteLink({ room }: { room: Room }) {
  const url = invitationUrl(room);
  const [feedback, setFeedback] = useState<Feedback>('idle');
  const [field, setField] = useState<HTMLInputElement | null>(null);
  const canShare = typeof navigator.share === 'function';

  useEffect(() => {
    if (feedback === 'idle') return;
    const timer = window.setTimeout(() => setFeedback('idle'), 2500);
    return () => window.clearTimeout(timer);
  }, [feedback]);

  async function share() {
    try {
      await navigator.share({ title: 'GameBattle', text: `Rejoins ma partie sur GameBattle !`, url });
    } catch {
      // Partage annulé par le joueur : rien à signaler.
    }
  }

  return (
    <div className="invite">
      <label className="field-label" htmlFor={`invite-${room.id}`}>
        Lien d’invitation
      </label>
      <div className="invite-row">
        <input
          ref={setField}
          id={`invite-${room.id}`}
          className="field-input invite-url"
          value={url}
          readOnly
          onFocus={(event) => event.currentTarget.select()}
          spellCheck={false}
        />
        <button type="button" className="tool-button" onClick={async () => setFeedback((await copy(url, field)) ? 'copied' : 'failed')}>
          {feedback === 'copied' ? 'Copié !' : 'Copier'}
        </button>
        {canShare ? (
          <button type="button" className="tool-button" onClick={share}>
            Partager
          </button>
        ) : null}
      </div>
      <p className="field-hint" aria-live="polite">
        {feedback === 'failed'
          ? 'Copie impossible ici : le lien est sélectionné, copie-le à la main.'
          : room.visibility === 'private'
            ? 'Seuls les joueurs qui ont ce lien peuvent entrer.'
            : 'Ta partie est aussi visible dans la liste des parties publiques.'}
      </p>
    </div>
  );
}
