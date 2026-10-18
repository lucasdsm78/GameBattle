import { useCallback, useEffect, useState } from 'react';

// Verrouille une action jusqu'à ce que `key` change (l'état serveur a avancé) ou, à défaut, après
// `unlockAfterMs` si le message s'est perdu : pas de double appui, pas d'interface bloquée.
export function useSendLock(key: string, unlockAfterMs = 1_500): [boolean, (action: () => void) => void] {
  const [lockedKey, setLockedKey] = useState<string | null>(null);

  useEffect(() => {
    if (lockedKey === null) return;
    const unlock = setTimeout(() => setLockedKey(null), unlockAfterMs);
    return () => clearTimeout(unlock);
  }, [lockedKey, unlockAfterMs]);

  const run = useCallback(
    (action: () => void) => {
      if (lockedKey === key) return;
      setLockedKey(key);
      action();
    },
    [key, lockedKey],
  );

  return [lockedKey === key, run];
}
