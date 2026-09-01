import type { MemoryState } from '../types/gameConfig';

type Props = {
  memory: MemoryState;
  teams: string[];
};

export function MemoryBoard({ memory, teams }: Props) {
  const currentTeam = teams[memory.current_team_index] ?? '—';
  const qualified = new Set(memory.qualified_team_indices);

  return (
    <section className="memory-board">
      <header className="memory-scoreboard">
        <div>
          <span className="memory-kicker">Mémoire en chaîne</span>
          <h2>{memory.phase === 'finished' ? 'Fin de la manche' : `Au tour de ${currentTeam}`}</h2>
        </div>
        <div className="memory-counter">
          <strong>{memory.sequence_length}</strong>
          <span>réponse{memory.sequence_length === 1 ? '' : 's'} à retenir</span>
        </div>
      </header>

      {memory.phase === 'idle' ? (
        <div className="memory-question-card memory-waiting">
          <span className="memory-brain">🧠</span>
          <h3>Préparez votre mémoire</h3>
          <p>L’équipe de départ sera tirée au hasard.</p>
        </div>
      ) : null}

      {memory.phase === 'question' && memory.current_question ? (
        <div className="memory-question-card">
          <span className="memory-turn">Question du tour {memory.turn_number}</span>
          <p>{memory.current_question.question}</p>
          <div className="memory-secret">🔒 Réponse visible uniquement par le présentateur</div>
        </div>
      ) : null}

      {memory.phase === 'finished' ? (
        <div className="memory-question-card memory-winner-card">
          <span>🏆 Vainqueur</span>
          <p>{memory.winner_team}</p>
        </div>
      ) : null}

      <div className="memory-team-grid">
        {teams.map((team, index) => (
          <div key={team} className={`memory-team ${qualified.has(index) || memory.phase === 'idle' ? 'is-qualified' : 'is-out'} ${index === memory.current_team_index && memory.phase === 'question' ? 'is-playing' : ''}`}>
            <span className="memory-team-status">{qualified.has(index) || memory.phase === 'idle' ? 'EN JEU' : 'ÉLIMINÉE'}</span>
            <strong>{team}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
