import { FlashCalcState } from '../types/gameConfig';
import { BuzzStreamBoard, StreamTimer } from './BuzzStreamBoard';

type Props = {
  game: FlashCalcState;
  teams: string[];
};

export function FlashCalcBoard({ game, teams }: Props) {
  const { verdict } = game;

  return (
    <BuzzStreamBoard
      title="Calcul flash"
      badge={<LevelMeter level={game.level} maxLevel={game.max_level} />}
      game={game}
      teams={teams}
      rules={
        <>
          <li>Des calculs défilent, de plus en plus vite et de plus en plus durs.</li>
          <li>
            Buzzez <strong>seulement si le résultat est juste</strong>.
          </li>
        </>
      }
    >
      {game.phase === 'running' ? (
        <>
          <div key={game.calc_number} className="fc-calc" aria-live="polite">
            <span>{game.expression}</span>
            <span className="fc-equals">=</span>
            <strong>{game.shown_result}</strong>
          </div>
          <StreamTimer key={`timer-${game.calc_number}`} durationMs={game.deadline_ms - game.shown_at_ms} />
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
            <p className="stream-correction">
              C’était <b>{verdict.true_result}</b>
            </p>
          )}
        </>
      ) : null}
    </BuzzStreamBoard>
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
