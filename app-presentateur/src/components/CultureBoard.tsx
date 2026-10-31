import { GameConfigSnapshot } from '../types/gameConfig';
import { RaceScoreboard } from './RaceScoreboard';

type Props = {
  gameConfig: GameConfigSnapshot;
};

export function CultureBoard({ gameConfig }: Props) {
  const culture = gameConfig.session.culture;
  const teams = gameConfig.settings.teams;
  const question = culture.current_question;
  const total = Math.max(culture.total_questions, 1);
  const tiebreak = culture.tiebreak_teams.length > 0;
  const progress = tiebreak ? 'Départage' : `${culture.current_index}/${total}`;

  return (
    <section className="chrono-layout">
      <article className="panel culture-stage">
        {culture.phase === 'idle' ? (
          <>
            <p className="section-chip">Culture générale</p>
            <div className="culture-waiting">En attente du présentateur…</div>
            <p className="chrono-state">10 questions — prépare-toi à buzzer !</p>
          </>
        ) : null}

        {culture.phase === 'selecting' && tiebreak ? (
          <>
            <div className="section-row">
              <span className="section-chip">Culture générale</span>
              <strong className="progress-pill">Départage</strong>
            </div>
            <div className="culture-waiting">Question de départage</div>
            <p className="culture-tiebreak-teams">{culture.tiebreak_teams.join(' · ')}</p>
            <p className="chrono-state">Une question difficile : la première bonne réponse remporte la manche.</p>
          </>
        ) : null}

        {culture.phase === 'selecting' && !tiebreak ? (
          <>
            <div className="section-row">
              <span className="section-chip">Culture générale</span>
              <strong className="progress-pill">{progress}</strong>
            </div>
            <div className="culture-waiting">Question {culture.current_index}</div>
            <p className="chrono-state">Choix de la difficulté en cours…</p>
          </>
        ) : null}

        {culture.phase === 'question' && question ? (
          <>
            <div className="section-row">
              <span className="section-chip">{tiebreak ? 'Question de départage' : 'Question'}</span>
              <strong className="progress-pill">{progress}</strong>
            </div>
            <p className="culture-question">{question.question}</p>
            {culture.answered ? (
              <div className="culture-answer">
                <span className="culture-answer-label">Réponse</span>
                <p className="culture-answer-text">{question.answer}</p>
                <p className="culture-answer-by">
                  {culture.current_buzzer_team ? `✓ Trouvé par ${culture.current_buzzer_team}` : 'Personne n’a trouvé'}
                </p>
              </div>
            ) : culture.current_buzzer_team ? (
              <div className="culture-buzzer">Au buzzer : {culture.current_buzzer_team}</div>
            ) : (
              <p className="chrono-state">
                {tiebreak ? `Départage : seules ${culture.tiebreak_teams.join(' et ')} peuvent buzzer !` : 'Buzzez pour répondre !'}
              </p>
            )}
          </>
        ) : null}

        {culture.phase === 'finished' ? <p className="chrono-state">Manche terminée</p> : null}
      </article>

      <RaceScoreboard
        teams={teams}
        scores={culture.scores}
        unit="point"
        highlight={culture.current_buzzer_team ? { team: culture.current_buzzer_team, tone: 'good' } : null}
        winnerTeam={culture.winner_team}
        excludedTeams={tiebreak ? teams.filter((team) => !culture.tiebreak_teams.includes(team)) : []}
        excludedLabel="Hors départage"
      />
    </section>
  );
}
