import { useEffect, useState } from 'react';

// Millisecondes restantes avant une échéance serveur. Le tick ne tourne que si `active`, et seul le
// composant qui appelle le hook se re-rend : on l'isole donc dans un petit composant d'affichage.
export function useCountdown(deadlineMs: number, active: boolean, tickMs = 200): number {
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const tick = setInterval(() => setNow(Date.now()), tickMs);
    return () => clearInterval(tick);
  }, [active, deadlineMs, tickMs]);

  return active ? Math.max(0, deadlineMs - now) : 0;
}
