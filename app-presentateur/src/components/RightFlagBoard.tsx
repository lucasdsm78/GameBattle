import { useEffect } from 'react';
import { flagUrl, preloadFlags } from '../lib/flags';
import { RightFlagState } from '../types/gameConfig';
import { BuzzStreamBoard, StreamTimer } from './BuzzStreamBoard';

type Props = {
  game: RightFlagState;
  teams: string[];
};

export function RightFlagBoard({ game, teams }: Props) {
  const { verdict } = game;
  const playing = game.phase !== 'idle' && game.phase !== 'paused';
  const missed = game.phase === 'feedback' && !verdict;

  useEffect(preloadFlags, []);

  return (
    <BuzzStreamBoard
      title="Le bon drapeau"
      badge={
        <span className="rf-progress">
          Drapeau {game.flag_number}/{game.flags_per_round}
        </span>
      }
      game={game}
      teams={teams}
      rules={
        <>
          <li>Un pays s’affiche, puis des drapeaux défilent.</li>
          <li>
            Buzzez <strong>seulement sur le bon drapeau</strong>.
          </li>
        </>
      }
    >
      {playing ? (
        <p className="rf-country">
          <span>Le drapeau de</span>
          <strong key={game.round_number}>{game.country_name}</strong>
        </p>
      ) : null}

      {game.phase === 'running' ? (
        <>
          <Flag key={`${game.round_number}-${game.flag_number}`} code={game.flag_code} />
          <StreamTimer key={`timer-${game.round_number}-${game.flag_number}`} durationMs={game.deadline_ms - game.shown_at_ms} />
        </>
      ) : null}

      {verdict ? (
        <>
          <Flag code={verdict.flag_code} label={verdict.flag_country} />
          {verdict.correct ? null : (
            <p className="stream-correction">
              Ce drapeau : <strong>{verdict.flag_country}</strong>
            </p>
          )}
        </>
      ) : null}

      {missed ? (
        <>
          <Flag code={game.country_code} label={game.country_name} />
          <p className="stream-correction">Personne n’a buzzé : c’était celui-ci !</p>
        </>
      ) : null}
    </BuzzStreamBoard>
  );
}

// Pendant le défilement, le texte alternatif reste neutre : il ne doit pas souffler le pays.
function Flag({ code, label }: { code: string; label?: string }) {
  const url = flagUrl(code);
  return (
    <figure className="rf-flag">
      {url ? <img src={url} alt={label ? `Drapeau : ${label}` : 'Drapeau'} draggable={false} /> : <span aria-hidden="true">🏳️</span>}
    </figure>
  );
}
