import { useState } from 'react';
import { Account, ApiError } from '../services/accountsApi';

type Props = { account: Account; onSignOut: () => Promise<void> };

export function WelcomeCard({ account, onSignOut }: Props) {
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signOut() {
    setLeaving(true);
    setError(null);
    try {
      await onSignOut();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'La déconnexion a échoué. Réessaie.');
      setLeaving(false);
    }
  }

  return (
    <section className="panel welcome-card" aria-labelledby="welcome-title">
      <p className="welcome-eyebrow">Joueur connecté</p>
      <h2 id="welcome-title" className="welcome-title">
        Salut, <span>{account.pseudo}</span> !
      </h2>
      <p className="welcome-text">Ton compte est prêt. Les parties en ligne arrivent bientôt : tu pourras rejoindre un salon avec un code, ou en un clic.</p>
      <p className="form-error" role="alert">
        {error}
      </p>
      <button type="button" className="secondary-button" onClick={signOut} disabled={leaving} aria-busy={leaving}>
        {leaving ? 'Déconnexion…' : 'Se déconnecter'}
      </button>
    </section>
  );
}
