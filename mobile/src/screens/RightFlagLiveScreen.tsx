import { StyleSheet, Text, View } from 'react-native';
import { BuzzStreamScreen, StreamTimer, streamStyles } from '../components/BuzzStreamScreen';
import { flagEmoji } from '../lib/flags';
import { colors } from '../theme';
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

export function RightFlagLiveScreen({ snapshot, ...actions }: Props) {
  const game = snapshot.session.right_flag;
  const { verdict } = game;
  const started = game.round_number > 0;
  const missed = game.phase === 'feedback' && !verdict;
  const shownFlag = verdict ? verdict.flag_code : missed ? game.country_code : game.flag_code;
  const onTarget = game.phase === 'running' && game.flag_code === game.country_code;

  const item =
    game.phase === 'running' || game.phase === 'feedback' || game.phase === 'finished' ? (
      <>
        <Text style={local.flag} accessibilityLabel="Drapeau affiché à l’écran">
          {flagEmoji(shownFlag)}
        </Text>
        {onTarget ? <Text style={local.targetTag}>👉 C’est le bon drapeau !</Text> : null}
        {verdict && !verdict.correct ? (
          <Text style={streamStyles.correction}>
            Ce drapeau : <Text style={local.wrongCountry}>{verdict.flag_country}</Text>
          </Text>
        ) : null}
        {missed ? <Text style={streamStyles.correction}>Personne n’a buzzé</Text> : null}
        {game.phase === 'running' ? (
          <StreamTimer key={`${game.round_number}-${game.flag_number}`} durationMs={game.deadline_ms - game.shown_at_ms} />
        ) : null}
      </>
    ) : null;

  const presenterOnly = started ? (
    <View style={local.answerCard}>
      <Text style={local.answerLabel}>Bon drapeau · visible uniquement sur la régie</Text>
      <View style={local.answerRow}>
        <Text style={local.answerFlag}>{flagEmoji(game.country_code)}</Text>
        <Text style={local.answerCountry} numberOfLines={2}>
          {game.country_name}
        </Text>
      </View>
    </View>
  ) : null;

  return (
    <BuzzStreamScreen
      snapshot={snapshot}
      game={game}
      title="Le bon drapeau"
      headlines={{
        idle: 'Prêts à reconnaître les drapeaux ?',
        running: started ? `Le drapeau de ${game.country_name}` : 'Le bon drapeau',
        revealed: `Personne n’a trouvé ${game.country_name}`,
      }}
      subtitle={started ? `Pays n°${game.round_number} · drapeau ${game.flag_number}/${game.flags_per_round}` : undefined}
      intro="Un pays s’affiche, puis des drapeaux défilent. Les équipes buzzent uniquement sur le bon drapeau :"
      itemKey={`${game.round_number}-${game.flag_number}`}
      item={item}
      presenterOnly={presenterOnly}
      {...actions}
    />
  );
}

const local = StyleSheet.create({
  flag: { fontSize: 120, lineHeight: 140, textAlign: 'center' },
  targetTag: { color: colors.accent, fontSize: 16, fontWeight: '900', textAlign: 'center' },
  wrongCountry: { color: colors.text },
  answerCard: {
    gap: 8,
    padding: 16,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: 'rgba(34,197,94,0.45)',
    backgroundColor: '#0f1f17',
  },
  answerLabel: { color: '#86efac', fontWeight: '800', fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase' },
  answerRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  answerFlag: { fontSize: 56, lineHeight: 66 },
  answerCountry: { flex: 1, color: colors.text, fontSize: 26, fontWeight: '900' },
});
