import { useEffect, useState } from 'react';

// Millisecondes restantes avant une échéance serveur ; le tick ne tourne que si `active`.
export function useCountdown(deadlineMs: number, active: boolean, tickMs = 200): number {
  const [now, setNow] = useState(Date.now);

  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const tick = window.setInterval(() => setNow(Date.now()), tickMs);
    return () => window.clearInterval(tick);
  }, [active, deadlineMs, tickMs]);

  return active ? Math.max(0, deadlineMs - now) : 0;
}
