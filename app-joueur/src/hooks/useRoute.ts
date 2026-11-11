import { useCallback, useEffect, useState } from 'react';

export type Route = { name: 'home' } | { name: 'invitation'; code: string };

const INVITATION_PATH = /^\/join\/([^/]+)\/?$/;

function decoded(segment: string): string | null {
  try {
    return decodeURIComponent(segment);
  } catch {
    return null; // « %E0%A4%A » et autres séquences invalides : `decodeURIComponent` lève une URIError
  }
}

/** Jamais d'exception ici : une adresse mal formée ne doit pas planter l'app au démarrage. */
function parse(pathname: string): Route {
  const match = pathname.match(INVITATION_PATH);
  if (!match) return { name: 'home' };
  // Code illisible : on reste sur l'écran d'invitation, qui dit que le lien n'est pas valide (code vide).
  return { name: 'invitation', code: decoded(match[1])?.toUpperCase() ?? '' };
}

const pathOf = (route: Route) => (route.name === 'invitation' ? `/join/${encodeURIComponent(route.code)}` : '/');

/** Deux adresses seulement (`/` et `/join/<code>`) : l'API History suffit, sans routeur à embarquer. */
export function useRoute() {
  const [route, setRoute] = useState<Route>(() => parse(window.location.pathname));

  useEffect(() => {
    const onPopState = () => setRoute(parse(window.location.pathname));
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  /** `replace` : une invitation consommée ne reste pas dans l'historique (le bouton retour ne la rejoue pas). */
  const navigate = useCallback((next: Route, { replace = false } = {}) => {
    const path = pathOf(next);
    if (window.location.pathname !== path) window.history[replace ? 'replaceState' : 'pushState'](null, '', path);
    setRoute(next);
  }, []);

  return { route, navigate };
}
