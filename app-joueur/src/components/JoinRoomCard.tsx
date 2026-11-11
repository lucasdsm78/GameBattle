import { FormEvent, useRef, useState } from 'react';
import { ApiError, errorMessage } from '../services/http';
import { Room, invitationCodeFrom, roomsApi } from '../services/roomsApi';
import { Disclosure } from './Disclosure';
import { Field, helpId } from './Field';
import { PublicRoomList } from './PublicRoomList';

type Props = {
  onJoined: (room: Room) => void;
  onInvitation: (code: string) => void;
  onCreatePublic: () => void;
  /** Recharge l'état réel du joueur (salon ou pas) quand on ne peut plus être sûr de ce que le serveur a fait. */
  onResync: () => void;
};
type Search = 'idle' | 'searching' | 'cancelling' | 'none';
type Option = 'list' | 'code' | null;

/** Rejoindre une partie : d'abord « Rejoindre rapidement », puis, si l'on préfère, la liste ou un code d'invitation. */
export function JoinRoomCard({ onJoined, onInvitation, onCreatePublic, onResync }: Props) {
  const [search, setSearch] = useState<Search>('idle');
  const [option, setOption] = useState<Option>(null);
  const [joining, setJoining] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [codeError, setCodeError] = useState<string | null>(null);
  const searchRequest = useRef<AbortController | null>(null);

  async function quickJoin() {
    const request = new AbortController();
    searchRequest.current = request;
    setSearch('searching');
    setError(null);
    try {
      const room = await roomsApi.quickJoin(request.signal);
      if (request.signal.aborted) await undoQuickJoin();
      else onJoined(room);
    } catch (caught) {
      if (request.signal.aborted) await undoQuickJoin();
      else if (caught instanceof ApiError && caught.status === 404) setSearch('none');
      else {
        setError(errorMessage(caught));
        setSearch('idle');
      }
    }
  }

  function cancel() {
    setSearch('cancelling');
    searchRequest.current?.abort();
  }

  /**
   * Annuler coupe la requête, mais le serveur a pu placer le joueur juste avant : on vérifie, et on ressort s'il le faut.
   * Si le départ échoue, la salle d'attente s'affiche (le joueur voit où il est et peut la quitter) ; si l'on ne peut
   * même pas vérifier, l'état réel est rechargé et l'échec annoncé : jamais d'accueil affiché à tort.
   */
  async function undoQuickJoin() {
    let room: Room | null;
    try {
      room = await roomsApi.current();
    } catch {
      setError('La recherche est annulée, mais le serveur ne répond pas : vérifie que tu n’es pas resté dans une partie.');
      setSearch('idle');
      onResync();
      return;
    }
    if (room) {
      try {
        await roomsApi.leave();
      } catch {
        onJoined(room); // le joueur reste membre : on lui montre son salon plutôt qu'un accueil trompeur
        return;
      }
    }
    setSearch('idle');
  }

  async function joinListed(roomId: string) {
    setJoining(roomId);
    setError(null);
    try {
      onJoined(await roomsApi.joinPublic(roomId));
    } catch (caught) {
      setError(errorMessage(caught));
      setJoining(null);
    }
  }

  function openCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = invitationCodeFrom(code);
    if (parsed) onInvitation(parsed);
    else setCodeError(code.trim() ? 'Ce lien ou ce code n’est pas valide : vérifie qu’il est complet.' : 'Colle le lien ou le code reçu.');
  }

  const toggle = (next: Exclude<Option, null>) => setOption((current) => (current === next ? null : next));

  return (
    <section className="panel play-card" aria-labelledby="join-title">
      <h2 id="join-title" className="section-title">
        Rejoindre une partie
      </h2>
      <p className="play-lead">Trouve rapidement une partie publique qui attend des joueurs.</p>

      {search === 'searching' || search === 'cancelling' ? (
        <div className="searching" role="status">
          <span className="loader is-small" aria-hidden="true" />
          <span>{search === 'searching' ? 'Recherche d’une partie…' : 'Annulation…'}</span>
          <button type="button" className="tool-button" onClick={cancel} disabled={search === 'cancelling'}>
            Annuler
          </button>
        </div>
      ) : (
        <button type="button" className="primary-button" onClick={quickJoin}>
          Rejoindre rapidement
        </button>
      )}

      {search === 'none' ? (
        <div className="no-room" role="status">
          <p>Aucune partie publique n’attend de joueurs pour l’instant.</p>
          <button type="button" className="tool-button" onClick={onCreatePublic}>
            Créer une partie publique
          </button>
        </div>
      ) : null}

      <p className="form-error" role="alert">
        {error}
      </p>

      <div className="join-options">
        <Disclosure question="Tu préfères choisir ?" action="Voir les parties publiques" open={option === 'list'} onToggle={() => toggle('list')}>
          <PublicRoomList joining={joining} onJoin={joinListed} />
        </Disclosure>
        <Disclosure question="Tu as reçu une invitation ?" action="Entrer un code" open={option === 'code'} onToggle={() => toggle('code')}>
          <form className="code-form" onSubmit={openCode} noValidate>
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
                  autoFocus
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
        </Disclosure>
      </div>
    </section>
  );
}
