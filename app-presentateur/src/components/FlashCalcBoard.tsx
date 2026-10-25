import { CSSProperties } from 'react';
import { FlashCalcState, FlashCalcVerdict } from '../types/gameConfig';
import { RaceScoreboard, ScoreHighlight } from './RaceScoreboard';

type Props = {
  game: FlashCalcState;
  teams: string[];
};

const pointsLabel = ({ correct, points }: FlashCalcVerdict): string => {
  if (correct) return '+1';
  return points < 0 ? '−1' : 'reste à 0';
};

export function FlashCalcBoard({ game, teams }: Props) {
  const verdict = game.verdict;
  const highlight: ScoreHighlight = verdict ? { team: verdict.team, tone: verdict.correct ? 'good' : 'bad' } : null;

  return (
    <section className="race-layout">
      <article className={`glass-card race-stage fc-stage ${verdict ? (verdict.correct ? 'is-good' : 'is-bad') : ''}`}>
        <div className="fc-topline">
          <p className="race-kicker">Calcul flash</p>
          {game.phase !== 'idle' ? <LevelMeter level={game.level} maxLevel={game.max_level} /> : null}
        </div>

        {game.phase === 'idle' ? (
          <ul className="fc-rules">
            <li>Des calculs défilent, de plus en plus vite et de plus en plus durs.</li>
            <li>Buzzez <strong>seulement si le résultat est juste</strong>.</li>
            <li>
              Juste : <b className="is-good">+1</b> · Faux : <b className="is-bad">−1</b> (jamais sous 0)
            </li>
          </ul>
        ) : null}

        {game.phase === 'paused' ? <p className="fc-paused">⏸ Pause</p> : null}

        {game.phase === 'running' ? (
          <>
            <div key={game.calc_number} className="fc-calc" aria-live="polite">
              <span>{game.expression}</span>
              <span className="fc-equals">=</span>
              <strong>{game.shown_result}</strong>
            </div>
            <CalcTimer key={`timer-${game.calc_number}`} durationMs={game.deadline_ms - game.shown_at_ms} />
            <p className="race-instruction">Buzzez seulement si c’est juste !</p>
          </>
        ) : null}

        {verdict ? (
          <>
            <div key={`verdict-${game.calc_number}`} className="fc-calc is-verdict">
              <span>{verdict.expression}</span>
              <span className="fc-equals">=</span>
              <strong>{verdict.correct ? verdict.shown_result : <s>{verdict.shown_result}</s>}</strong>
            </div>
            {verdict.correct ? null : (
              <p className="fc-correction">
                C’était <b>{verdict.true_result}</b>
              </p>
            )}
            <p className="fc-verdict" role="status">
              {verdict.correct ? '✓ Juste !' : '✕ Faux !'} {verdict.team} <b>{pointsLabel(verdict)}</b>
            </p>
          </>
        ) : null}
      </article>

      <RaceScoreboard
        teams={teams}
        scores={game.scores}
        goal={game.winning_score}
        unit="point"
        highlight={highlight}
        winnerTeam={game.winner_team}
      />
    </section>
  );
}

function LevelMeter({ level, maxLevel }: { level: number; maxLevel: number }) {
  return (
    <div className="fc-level" aria-label={`Niveau ${level} sur ${maxLevel}`}>
      <span key={level}>Niveau {level}</span>
      <span className="fc-level-pips" aria-hidden="true">
        {Array.from({ length: maxLevel }, (_, index) => (
          <i key={index} className={index < level ? 'is-on' : ''} />
        ))}
      </span>
    </div>
  );
}

// Barre purement CSS, relancée à chaque calcul : sa durée vient du serveur, sans dépendre de l'horloge du client.
function CalcTimer({ durationMs }: { durationMs: number }) {
  return (
    <div className="fc-timer" aria-hidden="true">
      <span style={{ animationDuration: `${Math.max(0, durationMs)}ms` } as CSSProperties} />
    </div>
  );
}
