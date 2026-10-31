import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
};

const seconds = (ms: number): string => `${(ms / 1000).toFixed(3).replace('.', ',')} s`;

export function StopChronoBoard({ gameConfig }: Props) {
  const chrono = gameConfig.session.stopchrono;
  const teams = gameConfig.settings.teams;
  const currentTeam = chrono.current_team;
  // Avec la rotation, la position dans le tour vient du nombre d'équipes qui ont déjà joué.
  const playedCount = Object.keys(chrono.results).length;
  const teamPosition = Math.min(chrono.phase === 'revealed' ? playedCount : playedCount + 1, teams.length);

  return (
    <section className="chrono-layout">
      <article className="panel chrono-stage">
        <p className="section-chip">
          {chrono.phase === 'finished' ? 'Manche terminée' : `Tour ${chrono.round_number}/${chrono.rounds_total} · cible à atteindre`}
        </p>
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
          <p className="chrono-state">
            {chrono.winner_team === 'Égalité'
              ? 'Égalité : même erreur totale !'
              : `${chrono.winner_team} gagne avec ${seconds(chrono.total_errors_ms[chrono.winner_team ?? ''] ?? 0)} d’erreur totale`}
          </p>
        )}
      </article>

      <aside className="panel chrono-scores">
        <p className="section-chip">Erreur totale · la plus petite gagne</p>
        <div className="chrono-score-list">
          {teams.map((team) => {
            const played = team in chrono.results;
            const active = team === currentTeam && chrono.phase !== 'finished';
            return (
              <div key={team} className={`chrono-score-item ${active ? 'chrono-score-item-active' : ''}`}>
                <span className="chrono-score-team">{team}</span>
                <span className="chrono-score-time">{seconds(chrono.total_errors_ms[team] ?? 0)}</span>
                <span className="chrono-score-delta">
                  {played ? `ce tour : ${seconds(chrono.results[team])} (écart ${seconds(chrono.deltas_ms[team] ?? 0)})` : 'pas encore joué ce tour'}
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
