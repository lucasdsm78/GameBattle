import { StyleSheet, Text } from 'react-native';
import { BuzzStreamScreen, STREAM_WARNING, StreamTimer, streamStyles } from '../components/BuzzStreamScreen';
import { colors, fonts } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onBuzz: (team: string) => void;
  onPause: () => void;
  onResume: () => void;
  onBack: () => void;
};

export function FlashCalcLiveScreen({ snapshot, ...actions }: Props) {
  const game = snapshot.session.flash_calc;
  const { verdict } = game;

  const item =
    game.phase === 'running' || verdict ? (
      <>
        <Text style={local.calcText} numberOfLines={1} adjustsFontSizeToFit accessibilityLiveRegion="polite">
          {verdict ? verdict.expression : game.expression} <Text style={local.equals}>=</Text>{' '}
          <Text style={!verdict ? local.result : verdict.correct ? streamStyles.good : local.struck}>
            {verdict ? verdict.shown_result : game.shown_result}
          </Text>
        </Text>
        {verdict && !verdict.correct ? (
          <Text style={streamStyles.correction}>
            C’était <Text style={streamStyles.good}>{verdict.true_result}</Text>
          </Text>
        ) : null}
        {game.phase === 'running' ? <StreamTimer key={game.calc_number} durationMs={game.deadline_ms - game.shown_at_ms} /> : null}
      </>
    ) : null;

  return (
    <BuzzStreamScreen
      snapshot={snapshot}
      game={game}
      title="Calcul flash"
      headlines={{ idle: 'Prêts à calculer ?', running: 'Juste ou faux ?', revealed: 'Juste ou faux ?' }}
      subtitle={game.calc_number > 0 ? `Calcul n°${game.calc_number} · Niveau ${game.level}/${game.max_level}` : undefined}
      intro="Les calculs défilent seuls, de plus en plus vite. Les équipes buzzent uniquement quand le résultat est juste :"
      itemKey={String(game.calc_number)}
      item={item}
      {...actions}
    />
  );
}

const local = StyleSheet.create({
  calcText: { color: colors.text, fontSize: 48, fontFamily: fonts.black, textAlign: 'center', fontVariant: ['tabular-nums'] },
  equals: { color: colors.muted },
  result: { color: STREAM_WARNING },
  struck: { color: '#fca5a5', textDecorationLine: 'line-through' },
});
