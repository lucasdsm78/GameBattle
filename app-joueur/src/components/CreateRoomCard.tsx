import { FormEvent, useState } from 'react';
import { errorMessage } from '../services/http';
import { CreateRoom, Room, RoomFormat, SOLO_MAX_PLAYERS, SOLO_MIN_PLAYERS, Visibility, roomsApi } from '../services/roomsApi';
import { Choice, ChoiceGroup } from './ChoiceGroup';
import { Stepper } from './Stepper';

const VISIBILITIES: readonly Choice<Visibility>[] = [
  { value: 'private', label: 'Privée', hint: 'Entre amis, avec ton lien' },
  { value: 'public', label: 'Publique', hint: 'Ouverte à tous les joueurs' },
];
const FORMATS: readonly Choice<RoomFormat>[] = [
  { value: 'solo', label: 'Chacun pour soi', hint: 'Chaque joueur joue pour sa peau' },
  { value: 'teams', label: 'En équipes', hint: 'Jusqu’à 4 joueurs par équipe' },
];
const TEAM_COUNTS: readonly Choice<'2' | '3' | '4'>[] = [
  { value: '2', label: '2' },
  { value: '3', label: '3' },
  { value: '4', label: '4' },
];

export function CreateRoomCard({ onCreated }: { onCreated: (room: Room) => void }) {
  const [settings, setSettings] = useState<CreateRoom>({ visibility: 'private', format: 'teams', team_count: 2, max_players: 4 });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const update = (change: Partial<CreateRoom>) => setSettings((current) => ({ ...current, ...change }));

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      onCreated(await roomsApi.create(settings));
    } catch (caught) {
      setError(errorMessage(caught));
      setSubmitting(false);
    }
  }

  return (
    <section className="panel play-card" aria-labelledby="create-title">
      <h2 id="create-title" className="section-title">
        Créer une partie
      </h2>
      <form className="play-form" onSubmit={onSubmit}>
        <ChoiceGroup legend="Qui peut entrer ?" choices={VISIBILITIES} value={settings.visibility} onChange={(visibility) => update({ visibility })} disabled={submitting} />
        <ChoiceGroup legend="Format" choices={FORMATS} value={settings.format} onChange={(format) => update({ format })} disabled={submitting} />
        {settings.format === 'solo' ? (
          <Stepper
            label="Joueurs maximum"
            value={settings.max_players}
            min={SOLO_MIN_PLAYERS}
            max={SOLO_MAX_PLAYERS}
            onChange={(max_players) => update({ max_players })}
            unit={['joueur', 'joueurs']}
            hint={`De ${SOLO_MIN_PLAYERS} à ${SOLO_MAX_PLAYERS} joueurs, toi compris.`}
            disabled={submitting}
          />
        ) : (
          <ChoiceGroup
            legend="Nombre d’équipes"
            choices={TEAM_COUNTS}
            value={String(settings.team_count) as '2' | '3' | '4'}
            onChange={(count) => update({ team_count: Number(count) })}
            disabled={submitting}
            compact
          />
        )}
        <p className="form-error" role="alert">
          {error}
        </p>
        <button type="submit" className="primary-button" disabled={submitting} aria-busy={submitting}>
          {submitting ? 'Création…' : 'Créer la partie'}
        </button>
      </form>
    </section>
  );
}
