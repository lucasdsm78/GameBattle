export type ScoreHighlight = { team: string; tone: 'good' | 'bad' } | null;

type Props = {
  teams: string[];
  scores: Record<string, number>;
  // « Premier à N » : une pastille par point (barre au-delà de MAX_DOTS). Sans objectif, le score seul.
  goal?: number;
  unit: string;
  keys?: string[];
  highlight?: ScoreHighlight;
  winnerTeam?: string | null;
  excludedTeams?: string[];
  excludedLabel?: string;
};

const MAX_DOTS = 12;

// Tableau des scores façon panneau d'affichage : le score rebondit à chaque changement.
export function RaceScoreboard({
  teams,
  scores,
  goal,
  unit,
  keys,
  highlight = null,
  winnerTeam = null,
  excludedTeams = [],
  excludedLabel,
}: Props) {
  return (
    <aside className="panel race-scores">
      <div className="section-row">
        <span className="section-chip">Scores</span>
        {goal ? <strong className="progress-pill">Objectif {goal}</strong> : null}
      </div>
      <ol className="race-score-list">
        {teams.map((team, index) => {
          const score = scores[team] ?? 0;
          const excluded = excludedTeams.includes(team);
          const label = `${score} ${unit}${score > 1 ? 's' : ''}${goal ? ` sur ${goal}` : ''}`;
          const classes = [
            'race-score',
            highlight?.team === team ? (highlight.tone === 'good' ? 'is-current' : 'is-penalty') : '',
            team === winnerTeam ? 'is-winner' : '',
            excluded ? 'is-excluded' : '',
          ].join(' ');
          return (
            <li key={team} className={classes}>
              <span className="score-index">{keys?.[index]?.toUpperCase() ?? index + 1}</span>
              <span className="race-score-team">
                <strong>{team}</strong>
                {goal && goal <= MAX_DOTS ? (
                  <span className="race-dots" aria-label={label}>
                    {Array.from({ length: goal }, (_, dot) => (
                      <i key={dot} className={dot < score ? 'is-filled' : ''} />
                    ))}
                  </span>
                ) : null}
                {goal && goal > MAX_DOTS ? (
                  <span className="race-bar" aria-label={label}>
                    <i style={{ transform: `scaleX(${Math.min(1, score / goal)})` }} />
                  </span>
                ) : null}
                {excluded && excludedLabel ? <small>{excludedLabel}</small> : null}
              </span>
              <b key={score} aria-label={goal ? undefined : label}>
                {score}
              </b>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
