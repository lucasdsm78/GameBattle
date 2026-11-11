import { AuthCard } from './components/AuthCard';
import { useAccount } from './hooks/useAccount';
import { useRoute } from './hooks/useRoute';
import { PlayerArea } from './screens/PlayerArea';

const GAMES = ['Blindtest', 'Culture', 'La bombe', 'Calcul flash', 'Le bon drapeau', 'Une famille en or', 'Le juste prix', 'Stop chrono'];

export default function App() {
  const { state, retry, signedIn, signOut, sessionLost } = useAccount();
  const { route, navigate } = useRoute();

  if (state.status === 'signed-in') {
    return <PlayerArea account={state.account} route={route} navigate={navigate} onSignOut={signOut} onSessionLost={sessionLost} />;
  }

  const invited = route.name === 'invitation';
  return (
    <main className="home">
      <header className="home-hero">
        <h1 className="logo">
          <span>Game</span> <b>Battle</b>
        </h1>
        <p className="tagline">Le jeu télé entre amis, depuis ton canapé.</p>
        {invited ? null : (
          <ul className="game-strip" aria-label="Quelques jeux au programme">
            {GAMES.map((game) => (
              <li key={game}>{game}</li>
            ))}
          </ul>
        )}
      </header>

      {state.status === 'loading' ? (
        <section className="panel auth-card is-loading" aria-busy="true" aria-label="Chargement de ton compte">
          <span className="loader" />
        </section>
      ) : state.status === 'unreachable' ? (
        <section className="panel status-card" role="alert">
          <h2 className="status-title">Connexion impossible</h2>
          <p className="welcome-text">{state.message}</p>
          <button type="button" className="primary-button" onClick={retry}>
            Réessayer
          </button>
        </section>
      ) : (
        <>
          {invited || state.notice ? (
            <p className="notice" role="status">
              {invited ? 'Tu es invité à une partie ! Connecte-toi ou crée ton compte pour la rejoindre.' : state.notice}
            </p>
          ) : null}
          <AuthCard onSignedIn={signedIn} />
        </>
      )}
    </main>
  );
}
