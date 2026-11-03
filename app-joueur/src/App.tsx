import { AuthCard } from './components/AuthCard';
import { WelcomeCard } from './components/WelcomeCard';
import { useAccount } from './hooks/useAccount';

const GAMES = ['Blindtest', 'Culture', 'La bombe', 'Calcul flash', 'Le bon drapeau', 'Une famille en or', 'Le juste prix', 'Stop chrono'];

export default function App() {
  const { state, signedIn, signOut } = useAccount();

  return (
    <main className="home">
      <header className="home-hero">
        <h1 className="logo">
          <span>Game</span> <b>Battle</b>
        </h1>
        <p className="tagline">Le jeu télé entre amis, depuis ton canapé.</p>
        <ul className="game-strip" aria-label="Quelques jeux au programme">
          {GAMES.map((game) => (
            <li key={game}>{game}</li>
          ))}
        </ul>
      </header>

      {state.status === 'loading' ? (
        <section className="panel auth-card is-loading" aria-busy="true" aria-label="Chargement de ton compte">
          <span className="loader" />
        </section>
      ) : state.status === 'guest' ? (
        <AuthCard onSignedIn={signedIn} />
      ) : (
        <WelcomeCard account={state.account} onSignOut={signOut} />
      )}
    </main>
  );
}
