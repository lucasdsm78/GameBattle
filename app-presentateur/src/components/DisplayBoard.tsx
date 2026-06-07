import { useEffect } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot | null;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  onBuzz: (team: string) => void;
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

export function DisplayBoard({ gameConfig, connectionState, errorMessage, onBuzz }: Props) {
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

      for (let index = 0; index < teams.length; index += 1) {
        if (matchesBinding(event, buzzerKeys[index] ?? '')) {
          onBuzz(teams[index]);
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameConfig?.settings.buzzer_keys, gameConfig?.settings.teams, onBuzz]);

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

  const { settings, session, status, updated_at } = gameConfig;
  const { blindtest, active_round } = session;
  const currentTrack = blindtest.current_track;
  const progressLabel = `${blindtest.current_track_index}/${Math.max(blindtest.total_tracks, 1)}`;
  const teams = settings.teams;
  const buzzerKeys = settings.buzzer_keys?.length ? settings.buzzer_keys : KEYBOARD_BINDINGS.slice(0, teams.length);
  const keyboardHints = teams.map((team, index) => `${(buzzerKeys[index] ?? '?').toUpperCase()} → ${team}`);

  return (
    <main className="screen blindtest-screen">
      <section className="hero glass-card">
        <div>
          <p className="eyebrow">Blindtest live</p>
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
              {currentTrack?.artwork_url ? <img src={currentTrack.artwork_url} alt={currentTrack.title} /> : <span>♪</span>}
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
  );
}

