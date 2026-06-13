import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
  connectionState: 'connecting' | 'connected' | 'disconnected';
};

export function FinalRankingBoard({ gameConfig, connectionState }: Props) {
  const session = gameConfig.session;
  // final_ranking est ordonné du dernier au 1er (ordre de révélation). On inverse l'affichage :
  // le meilleur révélé en haut, le dernier tout en bas.
  const revealed = session.final_ranking.slice(0, session.ranking_reveal_count).reverse();

  return (
    <main className="screen blindtest-screen">
      <section className="hero glass-card">
        <div>
          <p className="eyebrow">Partie terminée</p>
          <h1>Classement final</h1>
          <p className="meta">
            <span>{gameConfig.settings.game_title}</span>
            <span>•</span>
            <span>{session.total_rounds} manches</span>
          </p>
        </div>
        <div className="hero-aside">
          <div className={`badge badge-${connectionState}`}>{connectionState}</div>
        </div>
      </section>

      <section className="ranking-board glass-card">
        {revealed.length === 0 ? (
          <p className="chrono-state">Révélation en attente… (le présentateur appuie sur « Suivant »)</p>
        ) : null}
        {revealed.map((entry) => (
          <div key={entry.team} className={`ranking-row ${entry.rank === 1 ? 'ranking-row-winner' : ''}`}>
            <span className="ranking-rank">{entry.rank === 1 ? '🏆' : `${entry.rank}e`}</span>
            <span className="ranking-team">{entry.team}</span>
            <span className="ranking-score">
              {entry.manches_won} manche{entry.manches_won > 1 ? 's' : ''}
            </span>
          </div>
        ))}
      </section>
    </main>
  );
}
