import { useCallback, useEffect, useState } from 'react';

export type Route = { name: 'home' } | { name: 'invitation'; code: string };

const INVITATION_PATH = /^\/rejoindre\/([^/]+)\/?$/;

function parse(pathname: string): Route {
  const match = pathname.match(INVITATION_PATH);
  return match ? { name: 'invitation', code: decodeURIComponent(match[1]).toUpperCase() } : { name: 'home' };
}

const pathOf = (route: Route) => (route.name === 'invitation' ? `/rejoindre/${encodeURIComponent(route.code)}` : '/');

/** Deux adresses seulement (`/` et `/rejoindre/<code>`) : l'API History suffit, sans routeur à embarquer. */
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
