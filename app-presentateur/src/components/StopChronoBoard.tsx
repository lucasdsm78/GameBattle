import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
};

const seconds = (ms: number): string => `${(ms / 1000).toFixed(3).replace('.', ',')} s`;

export function StopChronoBoard({ gameConfig }: Props) {
  const chrono = gameConfig.session.stopchrono;
  const teams = gameConfig.settings.teams;
  const currentTeam = chrono.current_team;
  const teamPosition = Math.min(chrono.current_team_index + 1, teams.length);

  return (
    <section className="chrono-layout">
      <article className="glass-card chrono-stage">
        <p className="section-chip">Cible à atteindre</p>
        <div className="chrono-target">{chrono.target_seconds}s</div>

        {chrono.phase !== 'finished' ? (
          <>
            <p className="chrono-turn">
              Au tour de <strong>{currentTeam ?? '—'}</strong> · équipe {teamPosition}/{teams.length}
            </p>

            {chrono.phase === 'idle' ? <p className="chrono-state">En attente du départ…</p> : null}

            {chrono.phase === 'running' ? (
              <div className="chrono-running">
                <span className="chrono-running-label">Chrono en cours…</span>
              </div>
            ) : null}

            {chrono.phase === 'revealed' && currentTeam ? (
              <div className="chrono-reveal">
                <div className="chrono-reveal-time">{seconds(chrono.results[currentTeam] ?? 0)}</div>
                <div className="chrono-reveal-delta">écart {seconds(chrono.deltas_ms[currentTeam] ?? 0)}</div>
              </div>
            ) : null}
          </>
        ) : (
          <p className="chrono-state">Manche terminée</p>
        )}
      </article>

      <aside className="glass-card chrono-scores">
        <p className="section-chip">Temps des équipes</p>
        <div className="chrono-score-list">
          {teams.map((team) => {
            const played = team in chrono.results;
            const active = team === currentTeam && chrono.phase !== 'finished';
            return (
              <div key={team} className={`chrono-score-item ${active ? 'chrono-score-item-active' : ''}`}>
                <span className="chrono-score-team">{team}</span>
                <span className="chrono-score-time">{played ? seconds(chrono.results[team]) : '—'}</span>
                <span className="chrono-score-delta">
                  {played ? `écart ${seconds(chrono.deltas_ms[team] ?? 0)}` : 'en attente'}
                  {chrono.scores[team] ? ` · +${chrono.scores[team]}` : ''}
                </span>
              </div>
            );
          })}
        </div>
      </aside>
    </section>
  );
}
