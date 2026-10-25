export type ScoreHighlight = { team: string; tone: 'good' | 'bad' } | null;

type Props = {
  teams: string[];
  scores: Record<string, number>;
  goal: number;
  unit: string;
  highlight?: ScoreHighlight;
  winnerTeam?: string | null;
  excludedTeams?: string[];
  excludedLabel?: string;
};

// Au-delà, une barre de progression remplace les pastilles (ex. 300 points).
const MAX_DOTS = 12;

// Tableau des scores des jeux « premier à N » : une pastille par point, le score rebondit à chaque changement.
export function RaceScoreboard({ teams, scores, goal, unit, highlight = null, winnerTeam = null, excludedTeams = [], excludedLabel }: Props) {
  return (
    <aside className="glass-card race-scores">
      <div className="section-row">
        <span className="section-chip">Scores</span>
        <strong className="progress-pill">Objectif {goal}</strong>
      </div>
      <ol className="race-score-list">
        {teams.map((team, index) => {
          const score = scores[team] ?? 0;
          const excluded = excludedTeams.includes(team);
          const classes = [
            'race-score',
            highlight?.team === team ? (highlight.tone === 'good' ? 'is-current' : 'is-penalty') : '',
            team === winnerTeam ? 'is-winner' : '',
            excluded ? 'is-excluded' : '',
          ].join(' ');
          return (
            <li key={team} className={classes}>
              <span className="score-index">{index + 1}</span>
              <span className="race-score-team">
                <strong>{team}</strong>
                {goal <= MAX_DOTS ? (
                  <span className="race-dots" aria-label={`${score} ${unit}${score > 1 ? 's' : ''} sur ${goal}`}>
                    {Array.from({ length: goal }, (_, dot) => (
                      <i key={dot} className={dot < score ? 'is-filled' : ''} />
                    ))}
                  </span>
                ) : (
                  <span className="race-bar" aria-label={`${score} ${unit}${score > 1 ? 's' : ''} sur ${goal}`}>
                    <i style={{ transform: `scaleX(${Math.min(1, score / goal)})` }} />
                  </span>
                )}
                {excluded && excludedLabel ? <small>{excludedLabel}</small> : null}
              </span>
              <b key={score}>{score}</b>
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
