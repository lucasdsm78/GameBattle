import { CSSProperties, useMemo } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { VanishingWordState } from '../types/gameConfig';
import { RaceScoreboard } from './RaceScoreboard';

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
  const highlightedTeam = game.current_buzzer_team ?? (revealed ? game.round_winner : null);

  return (
    <section className="race-layout">
      <article className="panel race-stage">
        <p className="race-kicker">{KICKERS[game.phase]}</p>

        {game.phase === 'idle' ? (
          <p className="race-instruction">8 mots vont s’afficher. Mémorisez-les : l’un d’eux va disparaître !</p>
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
              <p className="claim-banner" aria-live="assertive">{game.current_buzzer_team} a la main</p>
            ) : (
              <p className="race-instruction">Buzzez dès que vous avez trouvé le mot manquant.</p>
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

      <RaceScoreboard
        teams={teams}
        scores={game.scores}
        goal={game.winning_score}
        unit="mot"
        highlight={highlightedTeam ? { team: highlightedTeam, tone: 'good' } : null}
        winnerTeam={game.winner_team}
        excludedTeams={hunting ? game.excluded_teams : []}
        excludedLabel="S’est trompée"
      />
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
