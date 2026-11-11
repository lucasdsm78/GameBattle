import { useState } from 'react';
import { Account } from '../services/accountsApi';
import { errorMessage } from '../services/http';

type Props = { account: Account; onSignOut: () => Promise<void> };

/** Bandeau du joueur connecté : logo compact, pseudo, déconnexion (qui ne réussit qu'une fois la session révoquée). */
export function AccountBar({ account, onSignOut }: Props) {
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signOut() {
    setLeaving(true);
    setError(null);
    try {
      await onSignOut();
    } catch (caught) {
      setError(errorMessage(caught, 'La déconnexion a échoué. Réessaie.'));
      setLeaving(false);
    }
  }

  return (
    <header className="account-bar">
      <p className="logo is-small" aria-label="GameBattle">
        <span>Game</span> <b>Battle</b>
      </p>
      <div className="account-chip">
        <span className="account-pseudo" title={account.pseudo}>
          {account.pseudo}
        </span>
        <button type="button" className="link-button" onClick={signOut} disabled={leaving} aria-busy={leaving}>
          {leaving ? 'Déconnexion…' : 'Se déconnecter'}
        </button>
      </div>
      {error ? (
        <p className="form-error account-error" role="alert">
          {error}
        </p>
      ) : null}
    </header>
  );
}
