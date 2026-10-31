import { CSSProperties, useMemo } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { GameConfigSnapshot, OpeningView } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
  gameLabel: string;
};

// Ouverture de manche, rythmée par l'horloge du serveur : les équipes entrent en scène, puis les règles.
export function OpeningOverlay({ gameConfig, gameLabel }: Props) {
  const opening = gameConfig.session.opening;
  const remainingMs = useCountdown(opening?.until_ms ?? 0, Boolean(opening), 100);
  if (!opening || remainingMs <= 0) return null;

  return (
    <div className="opening-overlay" role="status" aria-live="polite">
      {opening.stage === 'teams' ? (
        <TeamsIntro opening={opening} elapsedMs={opening.until_ms - opening.started_at_ms - remainingMs} gameConfig={gameConfig} />
      ) : (
        <RulesCard opening={opening} gameLabel={gameLabel} manche={gameConfig.session.manche_number} />
      )}
    </div>
  );
}

type TeamsIntroProps = { opening: OpeningView; elapsedMs: number; gameConfig: GameConfigSnapshot };

function TeamsIntro({ opening, elapsedMs, gameConfig }: TeamsIntroProps) {
  const { teams, buzzer_keys: keys } = gameConfig.settings;
  const index = Math.floor(Math.max(0, elapsedMs) / opening.team_intro_ms);

  if (index >= teams.length) {
    return (
      <div key="go" className="opening-go">
        <p className="opening-kicker">{teams.length} équipes sur le plateau</p>
        <p className="opening-title">Que la partie commence&nbsp;!</p>
      </div>
    );
  }
  return (
    <div key={index} className="opening-team">
      <p className="opening-kicker">
        Équipe {index + 1} sur {teams.length}
      </p>
      <p className="opening-title">{teams[index]}</p>
      {keys[index] ? (
        <p className="opening-key">
          Votre buzzer : <kbd>{keys[index].toUpperCase()}</kbd>
        </p>
      ) : null}
    </div>
  );
}

type RulesCardProps = { opening: OpeningView; gameLabel: string; manche: number };

function RulesCard({ opening, gameLabel, manche }: RulesCardProps) {
  // Barre CSS figée sur l'échéance : elle reprend au bon endroit après un rechargement.
  const barStyle = useMemo(() => {
    const total = opening.until_ms - opening.started_at_ms;
    const left = Math.max(0, opening.until_ms - Date.now());
    return { '--opening-from': `${Math.min(1, left / total)}`, animationDuration: `${left}ms` } as CSSProperties;
  }, [opening.started_at_ms, opening.until_ms]);

  if (!opening.rules) return null;
  return (
    <div className="panel opening-rules">
      <p className="opening-kicker">Manche {manche} · les règles</p>
      <p className="opening-game">{gameLabel}</p>
      <ol>
        {opening.rules.lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ol>
      <p className="opening-example">
        <b>Exemple</b>
        {opening.rules.example}
      </p>
      <div className="opening-bar" aria-hidden="true">
        <span key={opening.until_ms} style={barStyle} />
      </div>
    </div>
  );
}
