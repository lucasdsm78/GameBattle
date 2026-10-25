import { CSSProperties, useRef } from 'react';
import { GoldenFamilyState } from '../types/gameConfig';
import { RaceScoreboard, ScoreHighlight } from './RaceScoreboard';

type Props = {
  game: GoldenFamilyState;
  teams: string[];
};

const turnBanner = (game: GoldenFamilyState): string => {
  switch (game.phase) {
    case 'faceoff':
      return '🔔 Face-à-face : buzzez !';
    case 'duel':
      return `Face-à-face · ${game.current_team} répond`;
    case 'control':
      return `${game.control_team} a la main`;
    case 'steal':
      return game.current_team === game.steal_from
        ? `La main revient à ${game.current_team}`
        : `${game.current_team} tente de prendre la main`;
    case 'revealed':
    case 'finished':
      return 'Le tableau est révélé';
    default:
      return '';
  }
};

export function GoldenFamilyBoard({ game, teams }: Props) {
  const { question } = game;
  const highlight: ScoreHighlight = game.current_team ? { team: game.current_team, tone: 'good' } : null;

  return (
    <section className="race-layout">
      <article className="glass-card race-stage gf-stage">
        <div className="stream-topline">
          <p className="race-kicker gf-kicker">Une famille en or</p>
          {game.question_number > 0 ? <span className="gf-pill">Question {game.question_number}</span> : null}
        </div>

        {game.phase === 'idle' || !question ? (
          <ul className="stream-rules">
            <li>Face-à-face : la première équipe à buzzer répond.</li>
            <li>La réponse la plus citée prend la main : chaque bonne réponse rapporte ses points.</li>
            <li>
              3 fautes <b className="is-bad">✕✕✕</b> : les autres équipes peuvent prendre la main.
            </li>
          </ul>
        ) : (
          <>
            <h2 key={game.question_number} className="gf-question">
              {question.text}
            </h2>
            <p key={`${game.phase}-${game.current_team}`} className={`gf-turn is-${game.phase}`} aria-live="assertive">
              {turnBanner(game)}
            </p>
            <ol className="gf-board" style={{ '--gf-rows': Math.ceil(game.board.length / 2) } as CSSProperties}>
              {game.board.map((slot, index) => {
                const answer = question.answers[index];
                return (
                  <li key={index} className={`gf-slot ${slot.revealed ? 'is-revealed' : ''} ${slot.revealed && !slot.found_by ? 'is-missed' : ''}`}>
                    {slot.revealed ? (
                      <span className="gf-slot-face">
                        <span className="gf-answer">{answer.text}</span>
                        <b className="gf-points">{answer.points}</b>
                      </span>
                    ) : (
                      <span className="gf-slot-number">{index + 1}</span>
                    )}
                  </li>
                );
              })}
            </ol>
            <Strikes strikes={game.strikes} max={game.max_strikes} />
          </>
        )}
        <StrikeFlash misses={game.misses} />
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

function Strikes({ strikes, max }: { strikes: number; max: number }) {
  return (
    <div className="gf-strikes" aria-label={`${strikes} faute${strikes > 1 ? 's' : ''} sur ${max}`}>
      {Array.from({ length: max }, (_, index) => (
        <span key={index} className={index < strikes ? 'is-on' : ''}>
          ✕
        </span>
      ))}
    </div>
  );
}

// Grande croix rouge à chaque mauvaise réponse ; rien au chargement de l'écran (seulement les nouvelles fautes).
function StrikeFlash({ misses }: { misses: number }) {
  const initialMisses = useRef(misses);
  if (misses === initialMisses.current) return null;
  return (
    <div key={misses} className="gf-strike-flash" aria-hidden="true">
      ✕
    </div>
  );
}
