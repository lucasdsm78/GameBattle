import { useCallback, useEffect, useRef, useState } from 'react';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  gameConfig: GameConfigSnapshot;
  onBeginAfterRoll: () => void;
  onExplode: () => void;
};

const dieInstruction = (result: string, sound: string): string => {
  if (result === 'TIC') return `Le mot doit commencer par le son « ${sound} »`;
  if (result === 'TAC') return `Le mot doit finir par le son « ${sound} »`;
  return `Le mot doit commencer ou finir par le son « ${sound} »`;
};

const createAudioContext = (): AudioContext | null => {
  const AudioContextClass = window.AudioContext;
  return AudioContextClass ? new AudioContextClass() : null;
};

export function BombeBoard({ gameConfig, onBeginAfterRoll, onExplode }: Props) {
  const bombe = gameConfig.session.bombe;
  const teams = gameConfig.settings.teams;
  const currentTeam = teams[bombe.current_team_index] ?? '—';
  const rollerTeam = bombe.roller_team_index === null ? '—' : teams[bombe.roller_team_index] ?? '—';
  const audioContextRef = useRef<AudioContext | null>(null);
  const playedExplosionRef = useRef<number>(0);
  const [soundReady, setSoundReady] = useState(false);

  const enableSound = useCallback(async () => {
    const context = audioContextRef.current ?? createAudioContext();
    if (!context) return;
    audioContextRef.current = context;
    if (context.state === 'suspended') await context.resume();
    setSoundReady(context.state === 'running');
  }, []);

  const playExplosion = useCallback(() => {
    const context = audioContextRef.current;
    if (!context || context.state !== 'running') return;

    const duration = 1.35;
    const buffer = context.createBuffer(1, Math.ceil(context.sampleRate * duration), context.sampleRate);
    const data = buffer.getChannelData(0);
    for (let index = 0; index < data.length; index += 1) {
      const decay = Math.exp((-7 * index) / data.length);
      data[index] = (Math.random() * 2 - 1) * decay;
    }

    const noise = context.createBufferSource();
    const filter = context.createBiquadFilter();
    const gain = context.createGain();
    noise.buffer = buffer;
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(1200, context.currentTime);
    filter.frequency.exponentialRampToValueAtTime(80, context.currentTime + duration);
    gain.gain.setValueAtTime(0.9, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + duration);
    noise.connect(filter).connect(gain).connect(context.destination);
    noise.start();
  }, []);

  useEffect(() => {
    const unlock = () => void enableSound();
    window.addEventListener('pointerdown', unlock, { once: true });
    window.addEventListener('keydown', unlock, { once: true });
    return () => {
      window.removeEventListener('pointerdown', unlock);
      window.removeEventListener('keydown', unlock);
    };
  }, [enableSound]);

  useEffect(() => {
    if (bombe.phase !== 'rolling' || bombe.die_reveal_at_ms <= 0) return;
    const delay = Math.max(bombe.die_reveal_at_ms - Date.now(), 0);
    let retryTimer: number | undefined;
    const timer = window.setTimeout(() => {
      onBeginAfterRoll();
      retryTimer = window.setInterval(onBeginAfterRoll, 1_000);
    }, delay);
    return () => {
      window.clearTimeout(timer);
      if (retryTimer !== undefined) window.clearInterval(retryTimer);
    };
  }, [bombe.die_reveal_at_ms, bombe.phase, onBeginAfterRoll]);

  useEffect(() => {
    if (bombe.phase !== 'running' || bombe.deadline_at_ms <= 0) return;
    const delay = Math.max(bombe.deadline_at_ms - Date.now(), 0);
    let retryTimer: number | undefined;
    const timer = window.setTimeout(() => {
      onExplode();
      retryTimer = window.setInterval(onExplode, 1_000);
    }, delay);
    return () => {
      window.clearTimeout(timer);
      if (retryTimer !== undefined) window.clearInterval(retryTimer);
    };
  }, [bombe.deadline_at_ms, bombe.phase, onExplode]);

  useEffect(() => {
    if (bombe.phase !== 'exploded' || playedExplosionRef.current === bombe.deadline_at_ms) return;
    playedExplosionRef.current = bombe.deadline_at_ms;
    playExplosion();
  }, [bombe.deadline_at_ms, bombe.phase, playExplosion]);

  useEffect(() => () => void audioContextRef.current?.close(), []);

  return (
    <section className={`bombe-board glass-card bombe-${bombe.phase}`}>
      {bombe.phase === 'idle' ? (
        <>
          <p className="section-chip">La Bombe</p>
          <h2 className="bombe-waiting">Préparez-vous…</h2>
          <p className="chrono-state">Le présentateur va lancer la bombe.</p>
        </>
      ) : null}

      {bombe.phase === 'awaiting_roll' ? (
        <>
          <p className="section-chip">Lancer du dé</p>
          <div className="bombe-die">?</div>
          <h2 className="bombe-current-team">{rollerTeam}, buzzez pour lancer le dé</h2>
          <p className="bombe-instruction">Le dé choisira TIC, TAC ou BOUM.</p>
        </>
      ) : null}

      {bombe.phase === 'rolling' ? (
        <>
          <p className="section-chip">Le dé tourne…</p>
          <div className="bombe-die bombe-die-rolling" aria-label="Dé en rotation">TIC · TAC · BOUM</div>
          <p className="bombe-current-team">{rollerTeam} lance le dé</p>
        </>
      ) : null}

      {bombe.phase === 'running' ? (
        <>
          {bombe.tiebreak_round > 0 ? <p className="section-chip">Départage {bombe.tiebreak_round}</p> : null}
          <div className="bombe-die-result">{bombe.die_result}</div>
          <p className="bombe-rule">{dieInstruction(bombe.die_result, bombe.sound)}</p>
          <div className="bombe-orb" aria-label="Bombe en cours">💣</div>
          <p className="bombe-kicker">Son imposé</p>
          <div className="bombe-letter bombe-sound">{bombe.sound}</div>
          <p className="bombe-current-team">À {currentTeam} de jouer</p>
          <p className="bombe-instruction">Dites un mot, puis buzzez pour passer la bombe.</p>
          <div className="bombe-scoreboard" aria-label="Points de pénalité">
            {teams.map((team, index) => (
              <div
                key={team}
                className={`bombe-score ${bombe.eligible_team_indices.includes(index) ? '' : 'bombe-score-out'}`}
              >
                <span>{team}</span>
                <strong>{bombe.scores[team] ?? 0}</strong>
              </div>
            ))}
          </div>
          {!soundReady ? (
            <button type="button" className="sound-enable" onClick={enableSound}>Activer le son BOUM</button>
          ) : (
            <span className="sound-ready">Son activé</span>
          )}
        </>
      ) : null}

      {bombe.phase === 'exploded' ? (
        <div className="bombe-explosion" role="status" aria-live="assertive">
          <div className="bombe-boom">BOUM !</div>
          <p>La bombe a explosé chez <strong>{bombe.exploded_team}</strong></p>
          <div className="bombe-scoreboard" aria-label="Points de pénalité">
            {teams.map((team) => (
              <div key={team} className="bombe-score">
                <span>{team}</span>
                <strong>{bombe.scores[team] ?? 0}</strong>
              </div>
            ))}
          </div>
          {bombe.winner_team ? (
            <p className="bombe-winner">🏆 {bombe.winner_team} remporte la manche avec le moins de pénalités</p>
          ) : (
            <p className="bombe-winner">Égalité au plus petit score — préparez la partie décisive !</p>
          )}
          {!soundReady ? (
            <button
              type="button"
              className="sound-enable"
              onClick={async () => {
                await enableSound();
                playExplosion();
              }}
            >
              Jouer le son BOUM
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
