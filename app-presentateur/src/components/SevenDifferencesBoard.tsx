import { useEffect, useState } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
  onOpen: () => void;
};

export function SevenDifferencesBoard({ gameConfig, onOpen }: Props) {
  const game = gameConfig.session.seven_differences;
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (game.phase !== 'memorizing') return;

    setNow(Date.now());
    const tick = window.setInterval(() => setNow(Date.now()), 200);
    let retry: number | undefined;
    const timer = window.setTimeout(() => {
      onOpen();
      retry = window.setInterval(onOpen, 1_000);
    }, Math.max(game.reveal_at_ms - Date.now(), 0));
    return () => {
      window.clearInterval(tick);
      window.clearTimeout(timer);
      if (retry !== undefined) window.clearInterval(retry);
    };
  }, [game.phase, game.reveal_at_ms, onOpen]);

  const secondsLeft = Math.max(0, Math.ceil((game.reveal_at_ms - now) / 1000));
  const isMemorizing = game.phase === 'memorizing';
  const imageUrl = isMemorizing ? game.original_image_url : game.modified_image_url;
  const foundCount = 7 - game.differences_remaining;

  if (game.phase === 'idle') {
    return (
      <section className="seven-waiting glass-card">
        <span className="seven-eye" aria-hidden="true">👁️</span>
        <h2>Préparez-vous à observer</h2>
        <p>L’image originale apparaîtra pendant 25 secondes.</p>
      </section>
    );
  }

  return (
    <section className="seven-layout">
      <article className="seven-image-card glass-card">
        <div className="seven-image-heading">
          <div>
            <p className="section-chip">{isMemorizing ? 'Image originale' : 'Image modifiée'}</p>
            <h2>{game.title}</h2>
          </div>
          {isMemorizing ? (
            <div className="seven-countdown" aria-live="polite">
              <strong>{secondsLeft}</strong>
              <span>secondes</span>
            </div>
          ) : (
            <div className="seven-progress" aria-label={`${foundCount} différences trouvées sur 7`}>
              <strong>{foundCount}/7</strong>
              <span>trouvées</span>
            </div>
          )}
        </div>

        <div className="seven-picture-wrap">
          {imageUrl ? <img src={imageUrl} alt={`${game.title} — ${isMemorizing ? 'image originale' : 'image modifiée'}`} /> : null}
          {isMemorizing ? <div className="seven-timer-bar" style={{ '--timer-progress': `${Math.min(100, (secondsLeft / 25) * 100)}%` } as React.CSSProperties} /> : null}
        </div>

        <div className={`seven-callout seven-callout-${game.phase}`}>
          {isMemorizing ? (
            <><strong>Mémorisez chaque détail</strong><span>Les buzzers s’ouvriront à la fin du compte à rebours.</span></>
          ) : game.phase === 'claimed' ? (
            <><strong>{game.current_buzzer_team} a la main</strong><span>L’équipe continue tant que ses réponses sont correctes.</span></>
          ) : game.phase === 'finished' ? (
            <><strong>Les 7 différences ont été trouvées</strong><span>Manche terminée.</span></>
          ) : (
            <><strong>Buzzers ouverts</strong><span>La première équipe à buzzer prend la main.</span></>
          )}
        </div>
      </article>

      <aside className="seven-scoreboard glass-card">
        <div className="section-row">
          <span className="section-chip">Classement</span>
          <strong className="progress-pill">{foundCount}/7</strong>
        </div>
        <div className="seven-score-list">
          {gameConfig.settings.teams.map((team, index) => (
            <div
              key={team}
              className={`seven-score ${game.current_buzzer_team === team ? 'is-active' : ''} ${game.blocked_team === team ? 'is-blocked' : ''}`}
            >
              <span className="score-index">{index + 1}</span>
              <div>
                <strong>{team}</strong>
                <small>
                  {game.current_buzzer_team === team
                    ? 'A la main'
                    : game.blocked_team === team
                      ? 'Attend une autre équipe'
                      : 'Prête à buzzer'}
                </small>
              </div>
              <b>{game.scores[team] ?? 0}</b>
            </div>
          ))}
        </div>
      </aside>
    </section>
  );
}
