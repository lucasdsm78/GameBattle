import { CSSProperties, useMemo } from 'react';
import { useCountdown } from '../hooks/useCountdown';
import { mediaUrl } from '../services/backend';
import { FairPriceState, PriceItem, PriceResult } from '../types/gameConfig';

type Props = {
  game: FairPriceState;
};

const euros = (price: number): string => `${price.toLocaleString('fr-FR')} €`;
const seconds = (ms: number): string => `${(ms / 1000).toFixed(1).replace('.', ',')} s`;

const HINT_LABELS = { plus: 'C’est plus !', moins: 'C’est moins !' } as const;

export function FairPriceBoard({ game }: Props) {
  const running = game.phase === 'running';
  const lastResult = game.results[game.results.length - 1];
  const position = Math.min(game.results.length + 1, game.turn_order.length);

  return (
    <section className="race-layout">
      <article className="panel race-stage fp-stage">
        <div className="stream-topline">
          <span className="tag-dark">{game.band_label}</span>
          {game.phase !== 'finished' ? (
            <span className="tag-dark">
              Équipe {position}/{game.turn_order.length}
            </span>
          ) : null}
        </div>

        {running && game.current_item ? (
          <>
            <ItemPicture item={game.current_item} />
            <p className="fp-item-name">{game.current_item.name}</p>
            <TurnClock key={game.deadline_ms} deadlineMs={game.deadline_ms} turnMs={game.turn_ms} />
            {game.hint ? (
              <p key={game.proposals} className={`fp-hint is-${game.hint}`} aria-live="assertive">
                {HINT_LABELS[game.hint]}
              </p>
            ) : (
              <p className="race-instruction">À vous ! Annoncez un prix.</p>
            )}
          </>
        ) : null}

        {game.phase === 'ready' ? (
          <>
            <p className="race-instruction">Au tour de</p>
            <p className="claim-banner">{game.current_team}</p>
            <p className="race-instruction">L’objet apparaît dès que le présentateur lance le chrono.</p>
          </>
        ) : null}

        {!running && lastResult ? <LastResult result={lastResult} /> : null}
        <p className="fp-disclaimer">Prix constatés en {game.prices_checked_on}</p>
      </article>

      <aside className="panel race-scores">
        <div className="section-row">
          <span className="section-chip">Chronos</span>
          <strong className="progress-pill">Le plus rapide gagne</strong>
        </div>
        <ol className="race-score-list">
          {game.turn_order.map((team, index) => {
            const result = game.results[index];
            const current = team === game.current_team;
            const classes = ['race-score', current ? 'is-current' : '', team === game.winner_team ? 'is-winner' : ''].join(' ');
            return (
              <li key={team} className={classes}>
                <span className="score-index">{index + 1}</span>
                <span className="race-score-team">
                  <strong>{team}</strong>
                  <small className="fp-score-detail">
                    {result ? `${result.item.name} · ${euros(result.item.price ?? 0)}` : current ? (running ? 'En jeu' : 'Prochaine équipe') : 'À venir'}
                  </small>
                </span>
                <b>{result ? (result.found ? seconds(result.elapsed_ms) : '—') : ''}</b>
              </li>
            );
          })}
        </ol>
      </aside>
    </section>
  );
}

function ItemPicture({ item, compact = false }: { item: PriceItem; compact?: boolean }) {
  const url = mediaUrl('fair-price', item.image);
  return (
    <figure className={`fp-picture ${compact ? 'is-compact' : ''}`}>
      {url ? <img src={url} alt={item.name} draggable={false} /> : null}
      {!compact && item.credit ? <figcaption>{item.credit}</figcaption> : null}
    </figure>
  );
}

function LastResult({ result }: { result: PriceResult }) {
  return (
    <div className={`fp-result ${result.found ? 'is-found' : 'is-missed'}`} role="status">
      <ItemPicture item={result.item} compact />
      <div>
        <p className="fp-result-team">{result.team}</p>
        <p className="fp-result-price">{euros(result.item.price ?? 0)}</p>
        <p className="fp-result-time">
          {result.found ? `Trouvé en ${seconds(result.elapsed_ms)} · ${result.proposals} proposition${result.proposals > 1 ? 's' : ''}` : 'Temps écoulé'}
        </p>
      </div>
    </div>
  );
}

// Chrono qui monte (comme à la télé) ; seule cette partie se re-rend à chaque tick.
function TurnClock({ deadlineMs, turnMs }: { deadlineMs: number; turnMs: number }) {
  const remainingMs = useCountdown(deadlineMs, true, 100);
  const barStyle = useMemo(() => {
    const left = Math.max(0, deadlineMs - Date.now());
    return { '--fp-from': `${Math.min(1, left / turnMs)}`, animationDuration: `${left}ms` } as CSSProperties;
  }, [deadlineMs, turnMs]);

  return (
    <div className="fp-clock" role="timer" aria-label={`${Math.ceil(remainingMs / 1000)} secondes restantes`}>
      <strong>{seconds(turnMs - remainingMs)}</strong>
      <div className="fp-clock-track" aria-hidden="true">
        <span style={barStyle} />
      </div>
    </div>
  );
}
