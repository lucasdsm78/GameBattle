import { useEffect, useState } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
};

export function AuctionBoard({ gameConfig }: Props) {
  const game = gameConfig.session.auction;
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (game.phase !== 'running') return;

    setNow(Date.now());
    const tick = window.setInterval(() => setNow(Date.now()), 100);

    return () => {
      window.clearInterval(tick);
    };
  }, [game.deadline_at_ms, game.phase]);

  const secondsLeft = game.phase === 'running'
    ? Math.ceil(Math.max(0, game.deadline_at_ms - now) / 1_000)
    : 30;
  const status = game.phase === 'idle'
    ? 'Le présentateur prépare le premier thème.'
    : game.phase === 'bidding'
      ? 'À vos enchères ! Buzzez pour annoncer votre mise.'
      : game.phase === 'ready'
        ? 'Le chrono démarrera au signal du présentateur.'
        : game.phase === 'running'
          ? 'Donnez vos réponses, puis buzzez quand vous avez terminé.'
          : game.attempt_succeeded
            ? 'Enchère réussie !'
            : 'Enchère manquée : 2 points pour chaque adversaire.';

  return (
    <section className="auction-layout">
      <article className="glass-card auction-stage">
        <p className="auction-kicker">
          {game.phase === 'bidding' ? 'Phase d’enchères' : game.phase === 'running' ? '30 secondes' : 'L’Enchère'}
        </p>
        <h2 className="auction-prompt">{game.prompt || 'Le thème arrive…'}</h2>

        {game.active_team ? (
          <div className="auction-challenge">
            <span className="auction-team">{game.active_team}</span>
            <span className="auction-target">{game.target_count} réponse{game.target_count > 1 ? 's' : ''}</span>
          </div>
        ) : null}

        {game.phase === 'running' ? (
          <div className="auction-progress" aria-live="polite">
            <strong className={`auction-timer ${secondsLeft <= 5 ? 'auction-timer-danger' : ''}`}>{secondsLeft}</strong>
            <div className="auction-count">
              <strong>{game.correct_count}</strong>
              <span>/ {game.target_count}</span>
            </div>
          </div>
        ) : null}

        {game.phase === 'resolved' || game.phase === 'finished' ? (
          <div className={`auction-result ${game.attempt_succeeded ? 'auction-result-success' : 'auction-result-failure'}`}>
            <strong>{game.attempt_succeeded ? 'Réussi !' : 'Échoué'}</strong>
            <span>{game.correct_count} / {game.target_count} bonnes réponses</span>
          </div>
        ) : null}

        <p className="auction-instruction">{status}</p>
      </article>

      <aside className="glass-card auction-scores">
        <div className="section-row">
          <span className="section-chip">Scores</span>
          <strong className="progress-pill">Objectif 20</strong>
        </div>
        <div className="auction-score-list">
          {gameConfig.settings.teams.map((team, index) => {
            const isActive = team === game.active_team;
            const hasBuzzed = game.bidding_teams.includes(team);
            const points = game.points_awarded[team] ?? 0;
            return (
              <div key={team} className={`auction-score ${isActive ? 'auction-score-active' : ''} ${hasBuzzed ? 'auction-score-buzzed' : ''}`}>
                <span className="score-index">{index + 1}</span>
                <span className="auction-score-team">
                  <strong>{team}</strong>
                  <small>{hasBuzzed && game.phase === 'bidding' ? '⚡ A buzzé' : isActive ? 'Équipe en jeu' : ''}</small>
                </span>
                <strong>{game.scores[team] ?? 0}</strong>
                {points > 0 ? <span className="auction-points">+{points}</span> : null}
              </div>
            );
          })}
        </div>
      </aside>
    </section>
  );
}
