import { GameConfigSnapshot } from '../types/gameConfig';
import { ConnectionState, ShowHeader } from './ShowHeader';

type Props = {
  gameConfig: GameConfigSnapshot;
  connectionState: ConnectionState;
};

const rankLabel = (rank: number): string => (rank === 1 ? '1er' : `${rank}e`);

export function FinalRankingBoard({ gameConfig, connectionState }: Props) {
  const session = gameConfig.session;
  // final_ranking est ordonné du dernier au 1er (ordre de révélation). On inverse l'affichage :
  // le meilleur révélé en haut, le dernier tout en bas.
  const revealed = session.final_ranking.slice(0, session.ranking_reveal_count).reverse();

  return (
    <main className="screen ranking-screen">
      <ShowHeader
        gameConfig={gameConfig}
        connectionState={connectionState}
        gameLabel="Classement final"
        detail={`${session.total_rounds} manche${session.total_rounds > 1 ? 's' : ''}`}
      />

      <section className="panel ranking-board">
        {revealed.length === 0 ? <p className="race-instruction">Roulement de tambour… le classement arrive.</p> : null}
        {revealed.map((entry) => (
          <div key={entry.team} className={`ranking-row ${entry.rank === 1 ? 'ranking-row-winner' : ''}`}>
            <span className="ranking-rank">{rankLabel(entry.rank)}</span>
            <span className="ranking-team">{entry.team}</span>
            <span className="ranking-score">
              {entry.manches_won} manche{entry.manches_won > 1 ? 's' : ''} gagnée{entry.manches_won > 1 ? 's' : ''}
            </span>
          </div>
        ))}
      </section>
    </main>
  );
}
