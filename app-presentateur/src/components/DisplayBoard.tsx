import { useEffect } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';
import { StopChronoBoard } from './StopChronoBoard';
import { CultureBoard } from './CultureBoard';
import { FinalRankingBoard } from './FinalRankingBoard';
import { BombeBoard } from './BombeBoard';
import { MemoryBoard } from './MemoryBoard';
import { SevenDifferencesBoard } from './SevenDifferencesBoard';

type Props = {
  gameConfig: GameConfigSnapshot | null;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  onBuzz: (team: string) => void;
  onStartChrono: () => void;
  onStopChrono: () => void;
  onCultureBuzz: (team: string) => void;
  onBombeBuzz: (team: string) => void;
  onBombeBeginAfterRoll: () => void;
  onBombeExplode: () => void;
  onSevenDifferencesOpen: () => void;
  onSevenDifferencesBuzz: (team: string) => void;
};

const KEYBOARD_BINDINGS = ['1', '2', '3', '4', '5', '6'];

const normalizeKeyboardValue = (value: string): string => value.trim().toLowerCase().replace(/\s+/g, '');

const bindingAliases = (binding: string): string[] => {
  const normalized = normalizeKeyboardValue(binding);
  if (!normalized) {
    return [];
  }

  const aliases = new Set([normalized]);
  if (normalized.length === 1) {
    aliases.add(`digit${normalized}`);
    aliases.add(`numpad${normalized}`);
    aliases.add(`key${normalized}`);
  }

  const specialAliases: Record<string, string[]> = {
    space: ['space', 'spacebar', 'espace'],
    espace: ['space', 'spacebar', 'espace'],
    enter: ['enter', 'return', 'entree', 'entrée'],
    return: ['enter', 'return'],
    tab: ['tab', 'tabulation'],
    escape: ['escape', 'esc', 'echap', 'échap'],
    esc: ['escape', 'esc'],
    arrowup: ['arrowup', 'up', 'haut'],
    up: ['arrowup', 'up', 'haut'],
    arrowdown: ['arrowdown', 'down', 'bas'],
    down: ['arrowdown', 'down', 'bas'],
    arrowleft: ['arrowleft', 'left', 'gauche'],
    left: ['arrowleft', 'left', 'gauche'],
    arrowright: ['arrowright', 'right', 'droite'],
    right: ['arrowright', 'right', 'droite'],
  };

  for (const alias of specialAliases[normalized] ?? []) {
    aliases.add(alias);
  }

  return [...aliases];
};

const eventAliases = (event: KeyboardEvent): Set<string> => {
  const key = normalizeKeyboardValue(event.key === ' ' ? 'space' : event.key);
  const code = normalizeKeyboardValue(event.code);
  const compactCode = normalizeKeyboardValue(event.code.replace(/^(Key|Digit|Numpad|Arrow)/, ''));
  const aliases = new Set([key, code, compactCode]);

  if (event.code === 'Space') {
    aliases.add(' ');
    aliases.add('space');
    aliases.add('espace');
  }
  if (event.code === 'Enter') {
    aliases.add('enter');
    aliases.add('return');
  }

  return aliases;
};

const matchesBinding = (event: KeyboardEvent, binding: string): boolean => {
  const aliases = eventAliases(event);
  return bindingAliases(binding).some((candidate) => aliases.has(candidate));
};

export function DisplayBoard({
  gameConfig,
  connectionState,
  errorMessage,
  onBuzz,
  onStartChrono,
  onStopChrono,
  onCultureBuzz,
  onBombeBuzz,
  onBombeBeginAfterRoll,
  onBombeExplode,
  onSevenDifferencesOpen,
  onSevenDifferencesBuzz,
}: Props) {
  const chronoPhase = gameConfig?.session.stopchrono.phase;
  const chronoTeamIndex = gameConfig?.session.stopchrono.current_team_index;
  const culturePhase = gameConfig?.session.culture.phase;
  const bombePhase = gameConfig?.session.bombe.phase;
  const bombeTeamIndex = gameConfig?.session.bombe.current_team_index;
  const sevenDifferencesPhase = gameConfig?.session.seven_differences.phase;
  const sevenDifferencesBlockedTeam = gameConfig?.session.seven_differences.blocked_team;
  const activeGameKey = gameConfig?.session.active_round?.game_key ?? 'blindtest';

  useEffect(() => {
    if (!gameConfig?.settings.teams.length) {
      return;
    }

    const teams = gameConfig.settings.teams;
    const buzzerKeys = gameConfig.settings.buzzer_keys?.length
      ? gameConfig.settings.buzzer_keys
      : KEYBOARD_BINDINGS.slice(0, teams.length);

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) {
        return;
      }

      // Stop Chrono : seule la touche de l'équipe en cours (ou Espace) démarre puis arrête le chrono.
      if (activeGameKey === 'stopchrono') {
        const currentKey = buzzerKeys[chronoTeamIndex ?? 0] ?? '';
        if (!matchesBinding(event, currentKey) && !matchesBinding(event, 'space')) {
          return;
        }
        if (chronoPhase === 'idle') {
          onStartChrono();
        } else if (chronoPhase === 'running') {
          onStopChrono();
        }
        return;
      }

      // Culture générale : les touches d'équipe buzzent (uniquement quand une question est affichée).
      if (activeGameKey === 'culture') {
        if (culturePhase !== 'question') {
          return;
        }
        for (let index = 0; index < teams.length; index += 1) {
          if (matchesBinding(event, buzzerKeys[index] ?? '')) {
            onCultureBuzz(teams[index]);
            return;
          }
        }
        return;
      }

      if (activeGameKey === 'bombe') {
        if (bombePhase !== 'running' && bombePhase !== 'awaiting_roll') return;
        const currentIndex = bombeTeamIndex ?? 0;
        if (matchesBinding(event, buzzerKeys[currentIndex] ?? '')) {
          onBombeBuzz(teams[currentIndex]);
        }
        return;
      }

      if (activeGameKey === 'seven_differences') {
        if (sevenDifferencesPhase !== 'open') return;
        for (let index = 0; index < teams.length; index += 1) {
          if (teams[index] !== sevenDifferencesBlockedTeam && matchesBinding(event, buzzerKeys[index] ?? '')) {
            onSevenDifferencesBuzz(teams[index]);
            return;
          }
        }
        return;
      }

      for (let index = 0; index < teams.length; index += 1) {
        if (matchesBinding(event, buzzerKeys[index] ?? '')) {
          onBuzz(teams[index]);
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    culturePhase,
    bombePhase,
    bombeTeamIndex,
    onCultureBuzz,
    onBombeBuzz,
    onSevenDifferencesBuzz,
    gameConfig?.settings.buzzer_keys,
    gameConfig?.settings.teams,
    activeGameKey,
    chronoPhase,
    chronoTeamIndex,
    onBuzz,
    onStartChrono,
    onStopChrono,
    sevenDifferencesBlockedTeam,
    sevenDifferencesPhase,
  ]);

  if (!gameConfig) {
    return (
      <main className="screen empty-state">
        <div className="glass-card waiting-card">
          <p className="eyebrow">GameBattle Live Sync</p>
          <h1>Connexion à la partie…</h1>
          <p>Le présentateur prépare la soirée. L’écran se synchronisera automatiquement.</p>
          <div className={`badge badge-${connectionState}`}>{connectionState}</div>
          {errorMessage ? <p className="inline-error">{errorMessage}</p> : null}
        </div>
      </main>
    );
  }

  if (gameConfig.status === 'finished') {
    return <FinalRankingBoard gameConfig={gameConfig} connectionState={connectionState} />;
  }

  if (activeGameKey === 'stopchrono') {
    const chrono = gameConfig.session.stopchrono;
    const recap = gameConfig.settings.teams
      .map((team) => `${team} : ${((chrono.results[team] ?? 0) / 1000).toFixed(2)}s`)
      .join('   •   ');
    return (
      <>
        <main className="screen blindtest-screen">
          <section className="hero glass-card">
            <div>
              <p className="eyebrow">Stop Chrono live</p>
              <h1>{gameConfig.settings.game_title}</h1>
              <p className="meta">
                <span>Cible {chrono.target_seconds}s</span>
                <span>•</span>
                <span>{gameConfig.settings.teams.length} équipes</span>
                <span>•</span>
                <span>{gameConfig.session.active_round?.label ?? 'En attente'}</span>
              </p>
            </div>
            <div className="hero-aside">
              <div className={`badge badge-${connectionState}`}>{connectionState}</div>
              <div className={`badge badge-status badge-${gameConfig.status}`}>{gameConfig.status}</div>
            </div>
          </section>

          <StopChronoBoard gameConfig={gameConfig} />

          {errorMessage ? <div className="error-banner glass-card">{errorMessage}</div> : null}
        </main>

        {chrono.winner_team ? (
          <div className="winner-overlay">
            {chrono.winner_team === 'Égalité' ? (
              <>
                <p className="winner-eyebrow">Manche terminée</p>
                <p className="winner-name">Égalité&nbsp;!</p>
              </>
            ) : (
              <>
                <p className="winner-eyebrow">🏆 Vainqueur de la manche</p>
                <p className="winner-name">{chrono.winner_team}</p>
              </>
            )}
            <p className="winner-sub">{recap}</p>
          </div>
        ) : null}
      </>
    );
  }

  if (activeGameKey === 'culture') {
    const culture = gameConfig.session.culture;
    const recap = gameConfig.settings.teams.map((team) => `${team} : ${culture.scores[team] ?? 0}`).join('   •   ');
    return (
      <>
        <main className="screen blindtest-screen">
          <section className="hero glass-card">
            <div>
              <p className="eyebrow">Culture générale</p>
              <h1>{gameConfig.settings.game_title}</h1>
              <p className="meta">
                <span>{gameConfig.settings.teams.length} équipes</span>
                <span>•</span>
                <span>{gameConfig.session.active_round?.label ?? 'En attente'}</span>
              </p>
            </div>
            <div className="hero-aside">
              <div className={`badge badge-${connectionState}`}>{connectionState}</div>
              <div className={`badge badge-status badge-${gameConfig.status}`}>{gameConfig.status}</div>
            </div>
          </section>

          <CultureBoard gameConfig={gameConfig} />

          {errorMessage ? <div className="error-banner glass-card">{errorMessage}</div> : null}
        </main>

        {culture.winner_team ? (
          <div className="winner-overlay">
            {culture.winner_team === 'Égalité' ? (
              <>
                <p className="winner-eyebrow">Manche terminée</p>
                <p className="winner-name">Égalité&nbsp;!</p>
              </>
            ) : (
              <>
                <p className="winner-eyebrow">🏆 Vainqueur de la manche</p>
                <p className="winner-name">{culture.winner_team}</p>
              </>
            )}
            <p className="winner-sub">{recap}</p>
          </div>
        ) : null}
      </>
    );
  }

  if (activeGameKey === 'bombe') {
    return (
      <>
        <main className="screen blindtest-screen">
          <section className="hero glass-card">
            <div>
              <p className="eyebrow">La Bombe</p>
              <h1>{gameConfig.settings.game_title}</h1>
              <p className="meta">
                <span>{gameConfig.session.active_round?.label ?? 'En attente'}</span>
                <span>•</span>
                <span>{gameConfig.settings.teams.length} équipes</span>
              </p>
            </div>
            <div className="hero-aside">
              <div className={`badge badge-${connectionState}`}>{connectionState}</div>
            </div>
          </section>
          <BombeBoard
            gameConfig={gameConfig}
            onBeginAfterRoll={onBombeBeginAfterRoll}
            onExplode={onBombeExplode}
          />
          {errorMessage ? <div className="error-banner glass-card">{errorMessage}</div> : null}
        </main>
      </>
    );
  }

  if (activeGameKey === 'memory') {
    const memory = gameConfig.session.memory;
    return (
      <>
        <main className="screen memory-screen">
          <section className="hero glass-card">
            <div>
              <p className="eyebrow">Mémoire en chaîne</p>
              <h1>{gameConfig.settings.game_title}</h1>
              <p className="meta">
                <span>{gameConfig.session.active_round?.label ?? 'En attente'}</span>
                <span>•</span>
                <span>{gameConfig.settings.teams.length} équipes</span>
              </p>
            </div>
            <div className="hero-aside">
              <div className={`badge badge-${connectionState}`}>{connectionState}</div>
              <div className={`badge badge-status badge-${gameConfig.status}`}>{gameConfig.status}</div>
            </div>
          </section>

          <MemoryBoard memory={memory} teams={gameConfig.settings.teams} />
          {errorMessage ? <div className="error-banner glass-card">{errorMessage}</div> : null}
        </main>

        {memory.winner_team ? (
          <div className="winner-overlay">
            <p className="winner-eyebrow">🏆 Vainqueur de la manche</p>
            <p className="winner-name">{memory.winner_team}</p>
            <p className="winner-sub">Dernière équipe encore qualifiée</p>
          </div>
        ) : null}
      </>
    );
  }

  if (activeGameKey === 'seven_differences') {
    const game = gameConfig.session.seven_differences;
    const recap = gameConfig.settings.teams.map((team) => `${team} : ${game.scores[team] ?? 0}`).join('   •   ');
    return (
      <>
        <main className="screen seven-screen">
          <section className="hero glass-card">
            <div>
              <p className="eyebrow">Les 7 différences</p>
              <h1>{gameConfig.settings.game_title}</h1>
              <p className="meta">
                <span>{gameConfig.session.active_round?.label ?? 'En attente'}</span>
                <span>•</span>
                <span>{gameConfig.settings.teams.length} équipes</span>
              </p>
            </div>
            <div className="hero-aside">
              <div className={`badge badge-${connectionState}`}>{connectionState}</div>
              <div className={`badge badge-status badge-${gameConfig.status}`}>{gameConfig.status}</div>
            </div>
          </section>

          <SevenDifferencesBoard gameConfig={gameConfig} onOpen={onSevenDifferencesOpen} />
          {errorMessage ? <div className="error-banner glass-card">{errorMessage}</div> : null}
        </main>

        {game.winner_team ? (
          <div className="winner-overlay">
            <p className="winner-eyebrow">Manche terminée</p>
            <p className="winner-name">{game.winner_team === 'Égalité' ? 'Égalité !' : game.winner_team}</p>
            <p className="winner-sub">{recap}</p>
          </div>
        ) : null}
      </>
    );
  }

  const { settings, session, status, updated_at } = gameConfig;
  const { blindtest, active_round } = session;
  const currentTrack = blindtest.current_track;
  const progressLabel = `${blindtest.current_track_index}/${Math.max(blindtest.total_tracks, 1)}`;
  const teams = settings.teams;
  const buzzerKeys = settings.buzzer_keys?.length ? settings.buzzer_keys : KEYBOARD_BINDINGS.slice(0, teams.length);
  const keyboardHints = teams.map((team, index) => `${(buzzerKeys[index] ?? '?').toUpperCase()} → ${team}`);

  return (
    <>
      <main className="screen blindtest-screen">
      <section className="hero glass-card">
        <div>
          <p className="eyebrow">Live</p>
          <h1>{settings.game_title}</h1>
          <p className="meta">
            <span>Mode {settings.random_round_order ? 'aléatoire' : 'manuel'}</span>
            <span>•</span>
            <span>{teams.length} équipes</span>
            <span>•</span>
            <span>{active_round?.label ?? 'En attente de validation'}</span>
          </p>
        </div>
        <div className="hero-aside">
          <div className={`badge badge-${connectionState}`}>{connectionState}</div>
          <div className={`badge badge-status badge-${status}`}>{status}</div>
          <p className="timestamp">Mis à jour : {new Date(updated_at).toLocaleString('fr-FR')}</p>
        </div>
      </section>

      <section className="blindtest-layout">
        <article className="glass-card now-playing-card">
          <div className="section-row">
            <span className="section-chip">Musique en cours</span>
            <strong className="progress-pill">{progressLabel}</strong>
          </div>

          <div className="track-visual">
            <div className="artwork-placeholder">
              {blindtest.revealed && currentTrack?.artwork_url ? (
                <img src={currentTrack.artwork_url} alt={currentTrack.title} />
              ) : (
                <span>♪</span>
              )}
            </div>
            <div>
              <p className="muted-label">Titre</p>
              <h2>{blindtest.revealed && currentTrack ? currentTrack.title : 'Titre masqué'}</h2>
              <p className="muted-label">Artiste</p>
              <p className="track-subtitle">{blindtest.revealed && currentTrack ? currentTrack.artist : 'Artiste masqué'}</p>
            </div>
          </div>

          <div className="playback-grid">
            <div>
              <span>Lecture</span>
              <strong>{blindtest.playback_state}</strong>
            </div>
            <div>
              <span>Reste</span>
              <strong>{blindtest.tracks_remaining}</strong>
            </div>
            <div>
              <span>Buzzer</span>
              <strong>{blindtest.current_buzzer_team ?? '—'}</strong>
            </div>
          </div>

          {blindtest.playlist_name ? (
            <div className="playlist-meta-card">
              <span>Playlist</span>
              <strong>{blindtest.playlist_name}</strong>
              <p>
                Source {blindtest.playlist_provider || 'manual'}
                {blindtest.playlist_source_url ? (
                  <>
                    {' '}
                    •{' '}
                    <a href={blindtest.playlist_source_url} target="_blank" rel="noreferrer">
                      ouvrir
                    </a>
                  </>
                ) : null}
              </p>
            </div>
          ) : null}
        </article>

        <aside className="side-column">
          <article className="glass-card score-card">
            <div className="section-row">
              <span className="section-chip">Score blindtest</span>
              <span className="muted-copy">10 musiques max</span>
            </div>
            <div className="score-list">
              {teams.map((team, index) => (
                <button
                  key={team}
                  type="button"
                  className={`score-item ${blindtest.current_buzzer_team === team ? 'score-item-active' : ''}`}
                  onClick={() => onBuzz(team)}
                >
                  <span className="score-index">{index + 1}</span>
                  <span className="score-team-wrap">
                    <span className="score-team">{team}</span>
                    <span className="score-key">{(buzzerKeys[index] ?? '?').toUpperCase()}</span>
                  </span>
                  <strong>{blindtest.scores[team] ?? 0}</strong>
                </button>
              ))}
            </div>
          </article>

          <article className="glass-card hints-card">
            <p className="section-chip">Clavier Mac / PC / USB</p>
            <ul>
              {keyboardHints.map((hint) => (
                <li key={hint}>{hint}</li>
              ))}
            </ul>
            {blindtest.winner_team ? <p className="winner-banner">Vainqueur : {blindtest.winner_team}</p> : null}
          </article>
        </aside>
      </section>

      {errorMessage ? <div className="error-banner glass-card">{errorMessage}</div> : null}
      </main>

      {blindtest.winner_team ? (
        <div className="winner-overlay">
          {blindtest.winner_team === 'Égalité' ? (
            <>
              <p className="winner-eyebrow">Manche terminée</p>
              <p className="winner-name">Égalité&nbsp;!</p>
            </>
          ) : (
            <>
              <p className="winner-eyebrow">🏆 Vainqueur de la manche</p>
              <p className="winner-name">{blindtest.winner_team}</p>
            </>
          )}
          <p className="winner-sub">
            {teams.map((team) => `${team} : ${blindtest.scores[team] ?? 0}`).join('   •   ')}
          </p>
        </div>
      ) : null}
    </>
  );
}
