import { ReactNode } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  eyebrow: string;
  className: string;
  winnerTeam: string | null;
  scores: Record<string, number>;
  children: ReactNode;
};

// Enveloppe commune des écrans de jeu : en-tête, contenu, erreur et annonce du vainqueur de manche.
export function GameScreen({ gameConfig, connectionState, errorMessage, eyebrow, className, winnerTeam, scores, children }: Props) {
  const { settings, session, status } = gameConfig;
  const recap = settings.teams.map((team) => `${team} : ${scores[team] ?? 0}`).join('   •   ');

  return (
    <>
      <main className={`screen ${className}`}>
        <section className="hero glass-card">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{settings.game_title}</h1>
            <p className="meta">
              <span>{session.active_round?.label ?? 'En attente'}</span>
              <span>•</span>
              <span>{settings.teams.length} équipes</span>
            </p>
          </div>
          <div className="hero-aside">
            <div className={`badge badge-${connectionState}`}>{connectionState}</div>
            <div className={`badge badge-status badge-${status}`}>{status}</div>
          </div>
        </section>

        {children}
        {errorMessage ? <div className="error-banner glass-card">{errorMessage}</div> : null}
      </main>

      {winnerTeam ? (
        <div className="winner-overlay">
          <p className="winner-eyebrow">Manche terminée</p>
          <p className="winner-name">{winnerTeam === 'Égalité' ? 'Égalité !' : winnerTeam}</p>
          <p className="winner-sub">{recap}</p>
        </div>
      ) : null}
    </>
  );
}
