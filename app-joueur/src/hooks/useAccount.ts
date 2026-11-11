import { useCallback, useEffect, useState } from 'react';
import { Account, accountsApi } from '../services/accountsApi';
import { errorMessage, isAbort } from '../services/http';

export type AccountState =
  | { status: 'loading' }
  | { status: 'unreachable'; message: string }
  | { status: 'guest'; notice?: string }
  | { status: 'signed-in'; account: Account };

/** Session du joueur, vérifiée auprès du serveur : le cookie HttpOnly n'est pas lisible depuis la page. */
export function useAccount() {
  const [state, setState] = useState<AccountState>({ status: 'loading' });

  // Un serveur injoignable n'est pas « déconnecté » : on le dit, et on propose de réessayer.
  const check = useCallback((signal?: AbortSignal) => {
    setState({ status: 'loading' });
    accountsApi
      .me(signal)
      .then((account) => setState(account ? { status: 'signed-in', account } : { status: 'guest' }))
      .catch((error: unknown) => {
        if (isAbort(error)) return;
        setState({ status: 'unreachable', message: errorMessage(error, 'Impossible de joindre le serveur.') });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    check(controller.signal);
    return () => controller.abort();
  }, [check]);

  const signedIn = useCallback((account: Account) => setState({ status: 'signed-in', account }), []);

  // Le joueur ne quitte l'écran connecté qu'une fois la session révoquée par le serveur : la page ne peut pas
  // effacer le cookie HttpOnly, donc une déconnexion seulement locale le reconnecterait au prochain chargement.
  // En cas d'échec, l'erreur remonte à l'appelant, qui reste connecté et l'affiche.
  const signOut = useCallback(async () => {
    await accountsApi.logout();
    setState({ status: 'guest' });
  }, []);

  /** Le serveur ne reconnaît plus la session (expirée, ou déconnectée depuis un autre appareil). */
  const sessionLost = useCallback(() => setState({ status: 'guest', notice: 'Ta session a expiré : reconnecte-toi pour continuer.' }), []);

  return { state, retry: () => check(), signedIn, signOut, sessionLost };
}
