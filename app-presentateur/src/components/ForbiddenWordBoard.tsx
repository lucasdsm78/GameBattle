import { CSSProperties, useMemo } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { ForbiddenWordState, ForbiddenWordTurn } from '../types/gameConfig';

const RING_RADIUS = 54;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;
const DANGER_SECONDS = 10;

const words = (count: number) => `${count} mot${count > 1 ? 's' : ''}`;

type Props = {
  game: ForbiddenWordState;
};

export function ForbiddenWordBoard({ game }: Props) {
  const currentTurn = game.phase === 'running' ? game.turns[game.turns.length - 1] : undefined;
  const lastTurn = game.phase !== 'running' ? game.turns[game.turns.length - 1] : undefined;

  return (
    <section className="fw-layout">
      <article className="glass-card fw-stage">
        {game.phase === 'running' && currentTurn ? (
          <>
            <div className="fw-stage-header">
              <span className="fw-live"><i aria-hidden="true" />Live</span>
              <span className="fw-team-badge">{currentTurn.team}</span>
            </div>
            <div className="fw-scoreline">
              <TurnRing deadlineMs={game.deadline_at_ms} durationMs={game.turn_duration_ms} />
              <div className="fw-found" aria-live="polite">
                <strong>{currentTurn.found_words.length}</strong>
                <span>{currentTurn.found_words.length > 1 ? 'mots trouvés' : 'mot trouvé'}</span>
              </div>
            </div>
            <FoundReveal turn={currentTurn} />
            <WordFeed turn={currentTurn} />
          </>
        ) : (
          <>
            <p className="fw-kicker">{game.phase === 'finished' ? 'Manche terminée' : 'Au tour de'}</p>
            <h2 className="fw-team-name">{game.phase === 'finished' ? 'Le mot interdit' : game.current_team ?? '…'}</h2>
            <p className="fw-instruction">
              {game.phase === 'finished'
                ? 'Toutes les équipes ont joué leur minute.'
                : '60 secondes pour faire deviner un maximum de mots… sans jamais prononcer les mots interdits !'}
            </p>
            {lastTurn ? (
              <div className="fw-recap">
                <p className="fw-recap-title">
                  ⏱ Temps écoulé · <strong>{lastTurn.team}</strong> · {words(lastTurn.found_words.length)}
                </p>
                <WordFeed turn={lastTurn} />
              </div>
            ) : null}
          </>
        )}
      </article>

      <aside className="glass-card fw-scores">
        <div className="section-row">
          <span className="section-chip">Tableau des scores</span>
          <strong className="progress-pill">{game.turns.length}/{game.turn_order.length}</strong>
        </div>
        <ol className="fw-score-list">
          {game.turn_order.map((team, index) => {
            const played = index < game.turns.length;
            const isCurrent = team === game.current_team;
            const status = isCurrent ? (game.phase === 'running' ? 'En jeu' : 'Prochaine équipe') : played ? 'A joué' : 'À venir';
            return (
              <li key={team} className={`fw-score ${isCurrent ? 'is-current' : ''} ${team === game.winner_team ? 'is-winner' : ''}`}>
                <span className="score-index">{index + 1}</span>
                <span className="fw-score-team">
                  <strong>{team}</strong>
                  <small>{status}</small>
                </span>
                <b>{played ? game.scores[team] ?? 0 : '–'}</b>
              </li>
            );
          })}
        </ol>
      </aside>
    </section>
  );
}

type TurnRingProps = { deadlineMs: number; durationMs: number };

// Seul ce composant se re-rend chaque tick ; l'anneau est animé en CSS (fluide et sans JS par image).
function TurnRing({ deadlineMs, durationMs }: TurnRingProps) {
  const msLeft = useCountdown(deadlineMs, true);
  const seconds = Math.ceil(msLeft / 1000);
  // Figé par échéance : l'anneau reprend au bon endroit après un rechargement sans être perturbé par les ticks.
  const ringStyle = useMemo(() => {
    const remainingMs = Math.max(0, deadlineMs - Date.now());
    return {
      '--fw-ring-from': `${RING_CIRCUMFERENCE * (1 - Math.min(1, remainingMs / durationMs))}`,
      '--fw-ring-to': `${RING_CIRCUMFERENCE}`,
      animationDuration: `${remainingMs}ms`,
    } as CSSProperties;
  }, [deadlineMs, durationMs]);

  return (
    <div className={`fw-ring ${seconds <= DANGER_SECONDS ? 'is-danger' : ''}`} role="timer" aria-label={`${seconds} secondes restantes`}>
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle className="fw-ring-track" cx="60" cy="60" r={RING_RADIUS} />
        <circle
          key={deadlineMs}
          className="fw-ring-progress"
          cx="60"
          cy="60"
          r={RING_RADIUS}
          strokeDasharray={RING_CIRCUMFERENCE}
          style={ringStyle}
        />
      </svg>
      <strong>{seconds}</strong>
    </div>
  );
}

// Le mot n'est révélé qu'une fois trouvé : la clé relance l'animation à chaque nouveau mot.
function FoundReveal({ turn }: { turn: ForbiddenWordTurn }) {
  const count = turn.found_words.length;
  if (!count) return null;
  return (
    <div key={count} className="fw-reveal" role="status" aria-live="assertive">
      <span>✓ Trouvé !</span>
      <strong>{turn.found_words[count - 1]}</strong>
    </div>
  );
}

function WordFeed({ turn }: { turn: ForbiddenWordTurn }) {
  if (!turn.found_words.length && !turn.skipped_words.length) return null;
  return (
    <ul className="fw-feed">
      {turn.found_words.map((word) => (
        <li key={`found-${word}`} className="fw-chip is-found">✓ {word}</li>
      ))}
      {turn.skipped_words.map((word) => (
        <li key={`skipped-${word}`} className="fw-chip is-skipped">{word}</li>
      ))}
    </ul>
  );
}
