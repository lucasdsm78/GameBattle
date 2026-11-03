import { useCallback, useEffect, useState } from 'react';
import { Account, accountsApi } from '../services/accountsApi';

export type AccountState = { status: 'loading' } | { status: 'guest' } | { status: 'signed-in'; account: Account };

/** Session du joueur : vérifiée au chargement (le cookie HttpOnly n'est pas lisible depuis la page). */
export function useAccount() {
  const [state, setState] = useState<AccountState>({ status: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    accountsApi
      .me(controller.signal)
      .then((account) => setState(account ? { status: 'signed-in', account } : { status: 'guest' }))
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === 'AbortError')) setState({ status: 'guest' });
      });
    return () => controller.abort();
  }, []);

  const signedIn = useCallback((account: Account) => setState({ status: 'signed-in', account }), []);
  const signOut = useCallback(async () => {
    await accountsApi.logout();
    setState({ status: 'guest' });
  }, []);

  return { state, signedIn, signOut };
}
