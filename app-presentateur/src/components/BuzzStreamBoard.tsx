import { CSSProperties, ReactNode } from 'react';
import { BuzzStreamGame, BuzzVerdict } from '../types/gameConfig';
import { RaceScoreboard, ScoreHighlight } from './RaceScoreboard';

type Props = {
  title: string;
  badge?: ReactNode;
  game: BuzzStreamGame;
  teams: string[];
  rules: ReactNode;
  children: ReactNode;
};

const pointsLabel = ({ correct, points }: BuzzVerdict): string => {
  if (correct) return '+1';
  return points < 0 ? '−1' : 'reste à 0';
};

// Cadre commun des jeux « buzze seulement si… » : consignes, pause, verdict du dernier buzz et scores.
// Chaque jeu ne fournit que l'élément qui défile (`children`).
export function BuzzStreamBoard({ title, badge, game, teams, rules, children }: Props) {
  const { verdict } = game;
  const highlight: ScoreHighlight = verdict ? { team: verdict.team, tone: verdict.correct ? 'good' : 'bad' } : null;
  const tone = verdict ? (verdict.correct ? 'is-good' : 'is-bad') : '';

  return (
    <section className="race-layout">
      <article className={`glass-card race-stage stream-stage ${tone}`}>
        <div className="stream-topline">
          <p className="race-kicker">{title}</p>
          {game.phase !== 'idle' ? badge : null}
        </div>

        {game.phase === 'idle' ? (
          <ul className="stream-rules">
            {rules}
            <li>
              Juste : <b className="is-good">+1</b> · Faux : <b className="is-bad">−1</b> (jamais sous 0)
            </li>
          </ul>
        ) : null}

        {game.phase === 'paused' ? (
          <div className="stream-paused" role="status">
            <p>{game.auto_paused ? '⏸ Pause : personne ne joue ?' : '⏸ Pause'}</p>
            {game.auto_paused ? <span>La régie relance le défilement d’un appui.</span> : null}
          </div>
        ) : null}

        {children}

        {verdict ? (
          <p className="stream-verdict" role="status">
            {verdict.correct ? '✓ Juste !' : '✕ Faux !'} {verdict.team} <b>{pointsLabel(verdict)}</b>
          </p>
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

// Barre purement CSS, relancée à chaque élément (clé) : sa durée vient du serveur, sans dépendre de l'horloge du client.
export function StreamTimer({ durationMs }: { durationMs: number }) {
  return (
    <div className="stream-timer" aria-hidden="true">
      <span style={{ animationDuration: `${Math.max(0, durationMs)}ms` } as CSSProperties} />
    </div>
  );
}
