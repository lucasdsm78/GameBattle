import { ReactNode } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';
import { OpeningOverlay } from './OpeningOverlay';
import { ConnectionState, ShowHeader } from './ShowHeader';

const TIE = 'Égalité';

type Props = {
  gameConfig: GameConfigSnapshot;
  connectionState: ConnectionState;
  errorMessage: string | null;
  gameLabel: string;
  detail?: string;
  className: string;
  winnerTeam: string | null;
  scores?: Record<string, number>;
  // Ligne sous le nom du vainqueur ; par défaut, les scores de chaque équipe.
  recap?: string;
  children: ReactNode;
};

// Enveloppe commune des écrans de jeu : habillage d'émission, contenu, erreur et annonce du vainqueur de manche.
export function GameScreen({ gameConfig, connectionState, errorMessage, gameLabel, detail, className, winnerTeam, scores, recap, children }: Props) {
  const scoreRecap = scores ? gameConfig.settings.teams.map((team) => `${team} ${scores[team] ?? 0}`).join('  ·  ') : '';

  return (
    <>
      <main className={`screen ${className}`}>
        <ShowHeader gameConfig={gameConfig} connectionState={connectionState} gameLabel={gameLabel} detail={detail} />
        {children}
        {errorMessage ? (
          <div className="error-banner" role="alert">
            {errorMessage}
          </div>
        ) : null}
      </main>

      <OpeningOverlay gameConfig={gameConfig} gameLabel={gameLabel} />
      {winnerTeam ? <WinnerOverlay winnerTeam={winnerTeam} recap={recap ?? scoreRecap} /> : null}
    </>
  );
}

function WinnerOverlay({ winnerTeam, recap }: { winnerTeam: string; recap: string }) {
  const tie = winnerTeam === TIE;
  return (
    <div className="winner-overlay" role="status" aria-live="assertive">
      <div className="winner-marquee">
        <p className="winner-eyebrow">{tie ? 'Manche terminée' : 'Vainqueur de la manche'}</p>
        <p className="winner-name">{tie ? 'Égalité !' : winnerTeam}</p>
        {recap ? <p className="winner-sub">{recap}</p> : null}
      </div>
    </div>
  );
}
