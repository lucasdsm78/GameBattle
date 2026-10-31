import { GameConfigSnapshot } from '../types/gameConfig';

export type ConnectionState = 'connecting' | 'connected' | 'disconnected';

type Props = {
  gameConfig: GameConfigSnapshot;
  connectionState: ConnectionState;
  gameLabel: string;
  detail?: string;
};

const CONNECTION_LABELS: Record<Exclude<ConnectionState, 'connected'>, string> = {
  connecting: 'Connexion…',
  disconnected: 'Connexion perdue',
};

// Habillage d'émission commun à tous les écrans : logo, nom du jeu, manche en cours et état du direct.
export function ShowHeader({ gameConfig, connectionState, gameLabel, detail }: Props) {
  const { session, settings } = gameConfig;

  return (
    <header className="show-header">
      <div className="show-logo" aria-label="GameBattle">
        <span>Game</span>
        <b>Battle</b>
      </div>
      <div className="show-title">
        <p className="show-game">
          {gameLabel}
          {detail ? <small>{detail}</small> : null}
        </p>
        <h1>{settings.game_title}</h1>
      </div>
      <div className="show-status">
        {session.total_rounds && gameConfig.status !== 'finished' ? (
          <p className="show-round">
            Manche <b>{session.manche_number}</b>
            <small>/{session.total_rounds}</small>
          </p>
        ) : null}
        {connectionState === 'connected' ? (
          <p className="show-live">
            <i aria-hidden="true" />
            En direct
          </p>
        ) : (
          <p className={`show-connection is-${connectionState}`} role="status">
            {CONNECTION_LABELS[connectionState]}
          </p>
        )}
      </div>
    </header>
  );
}
