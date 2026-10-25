import { CSSProperties, useMemo } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { VanishingWordState } from '../types/gameConfig';

type Props = {
  game: VanishingWordState;
  teams: string[];
};

const KICKERS: Record<VanishingWordState['phase'], string> = {
  idle: 'Le mot qui disparaît',
  memorizing: 'Mémorisez !',
  vanished: 'Quel mot a disparu ?',
  claimed: 'Quel mot a disparu ?',
  revealed: 'C’était…',
  finished: 'C’était…',
};

export function VanishingWordBoard({ game, teams }: Props) {
  const hunting = game.phase === 'vanished' || game.phase === 'claimed';
  const revealed = game.phase === 'revealed' || game.phase === 'finished';

  return (
    <section className="vw-layout">
      <article className="glass-card vw-stage">
        <p className="vw-kicker">{KICKERS[game.phase]}</p>

        {game.phase === 'idle' ? (
          <p className="vw-instruction">8 mots vont s’afficher. Mémorisez-les : l’un d’eux va disparaître !</p>
        ) : null}

        {game.phase === 'memorizing' ? (
          <>
            <MemorizationBar deadlineMs={game.reveal_at_ms} durationMs={game.memorization_ms} />
            <WordGrid words={game.words} />
          </>
        ) : null}

        {hunting ? (
          <>
            {game.current_buzzer_team ? (
              <p className="vw-claim" aria-live="assertive">🔔 {game.current_buzzer_team} a la main</p>
            ) : (
              <p className="vw-instruction">Buzzez dès que vous avez trouvé le mot manquant.</p>
            )}
            <WordGrid words={game.remaining_words} mysterySlot />
          </>
        ) : null}

        {revealed ? (
          <>
            <div key={game.round_number} className="vw-reveal" role="status">
              <strong>{game.vanished_word}</strong>
              <span>{game.round_winner ? `✓ Trouvé par ${game.round_winner}` : 'Personne n’a trouvé'}</span>
            </div>
            <WordGrid words={game.words} highlighted={game.vanished_word} />
          </>
        ) : null}
      </article>

      <aside className="glass-card vw-scores">
        <div className="section-row">
          <span className="section-chip">Scores</span>
          <strong className="progress-pill">Objectif {game.winning_score}</strong>
        </div>
        <ol className="vw-score-list">
          {teams.map((team, index) => {
            const score = game.scores[team] ?? 0;
            const excluded = hunting && game.excluded_teams.includes(team);
            const classes = [
              'vw-score',
              team === game.current_buzzer_team ? 'is-current' : '',
              team === game.winner_team || (revealed && team === game.round_winner) ? 'is-winner' : '',
              excluded ? 'is-excluded' : '',
            ].join(' ');
            return (
              <li key={team} className={classes}>
                <span className="score-index">{index + 1}</span>
                <span className="vw-score-team">
                  <strong>{team}</strong>
                  <span className="vw-dots" aria-label={`${score} mot${score > 1 ? 's' : ''} sur ${game.winning_score}`}>
                    {Array.from({ length: game.winning_score }, (_, dot) => (
                      <i key={dot} className={dot < score ? 'is-filled' : ''} />
                    ))}
                  </span>
                  {excluded ? <small>S’est trompée</small> : null}
                </span>
                <b>{score}</b>
              </li>
            );
          })}
        </ol>
      </aside>
    </section>
  );
}

type WordGridProps = { words: string[]; mysterySlot?: boolean; highlighted?: string };

function WordGrid({ words, mysterySlot = false, highlighted }: WordGridProps) {
  return (
    <ul className="vw-grid">
      {words.map((word, index) => (
        <li key={word} className={`vw-word ${word === highlighted ? 'is-vanished' : ''}`} style={{ '--vw-index': index } as CSSProperties}>
          {word}
        </li>
      ))}
      {mysterySlot ? <li className="vw-word is-mystery" aria-label="Mot disparu">?</li> : null}
    </ul>
  );
}

type BarProps = { deadlineMs: number; durationMs: number };

// Seul ce composant se re-rend chaque tick ; la barre est animée en CSS, figée par échéance.
function MemorizationBar({ deadlineMs, durationMs }: BarProps) {
  const seconds = Math.ceil(useCountdown(deadlineMs, true) / 1000);
  const barStyle = useMemo(() => {
    const remainingMs = Math.max(0, deadlineMs - Date.now());
    return { '--vw-from': `${Math.min(1, remainingMs / durationMs)}`, animationDuration: `${remainingMs}ms` } as CSSProperties;
  }, [deadlineMs, durationMs]);

  return (
    <div className="vw-timer" role="timer" aria-label={`Un mot disparaît dans ${seconds} secondes`}>
      <strong>{seconds}</strong>
      <div className="vw-timer-track">
        <span key={deadlineMs} style={barStyle} />
      </div>
    </div>
  );
}
