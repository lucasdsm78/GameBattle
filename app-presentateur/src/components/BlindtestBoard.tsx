import { GameConfigSnapshot } from '../types/gameConfig';
import { RaceScoreboard } from './RaceScoreboard';

type Props = {
  gameConfig: GameConfigSnapshot;
  buzzerKeys: string[];
};

export function BlindtestBoard({ gameConfig, buzzerKeys }: Props) {
  const { blindtest } = gameConfig.session;
  const track = blindtest.revealed ? blindtest.current_track : null;
  const playing = blindtest.playback_state === 'playing';
  const buzzer = blindtest.current_buzzer_team;

  return (
    <section className="race-layout">
      <article className="panel race-stage bt-stage">
        <div className="stream-topline">
          <span className="tag-dark">
            Titre {Math.max(blindtest.current_track_index, 1)}/{Math.max(blindtest.total_tracks, 1)}
          </span>
        </div>

        <div className={`bt-record ${playing ? 'is-playing' : ''}`} aria-hidden="true">
          <div className="bt-label">{track?.artwork_url ? <img src={track.artwork_url} alt="" /> : <span>?</span>}</div>
        </div>

        {track ? (
          <div key={track.track_id} className="bt-reveal" role="status">
            <strong>{track.title}</strong>
            <span>{track.artist}</span>
          </div>
        ) : buzzer ? (
          <p className="claim-banner" aria-live="assertive">
            {buzzer} a la main
          </p>
        ) : (
          <p className="race-instruction">{playing ? 'Écoutez… et buzzez dès que vous reconnaissez le titre !' : 'Prochain extrait dans un instant'}</p>
        )}
      </article>

      <RaceScoreboard
        teams={gameConfig.settings.teams}
        scores={blindtest.scores}
        unit="point"
        keys={buzzerKeys}
        highlight={buzzer ? { team: buzzer, tone: 'good' } : null}
        winnerTeam={blindtest.winner_team}
      />
    </section>
  );
}
