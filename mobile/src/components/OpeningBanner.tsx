import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useCountdown } from '../hooks/useCountdown';
import { useSendLock } from '../hooks/useSendLock';
import { colors, fonts, styles } from '../theme';
import { OpeningView } from '../types/gameConfig';

type Props = {
  opening: OpeningView;
  onSkip: () => void;
};

// Ce que montre l'écran pendant l'ouverture de la manche : la régie peut lire les règles à voix haute,
// puis passer à la suite (le premier coup joué ferme aussi l'écran des règles).
export function OpeningBanner({ opening, onSkip }: Props) {
  const seconds = Math.ceil(useCountdown(opening.until_ms, true) / 1000);
  const [skipping, skipOnce] = useSendLock(`${opening.stage}-${opening.started_at_ms}`);
  const teams = opening.stage === 'teams';

  return (
    <View style={local.card}>
      <View style={styles.sectionHeader}>
        <Text style={local.kicker}>À l’écran</Text>
        <Text style={local.seconds}>{seconds} s</Text>
      </View>
      <Text style={local.title}>{teams ? 'Présentation des équipes' : 'Les règles de la manche'}</Text>
      {opening.rules ? (
        <View style={local.rules}>
          {opening.rules.lines.map((line, index) => (
            <Text key={line} style={local.rule}>
              <Text style={local.ruleIndex}>{index + 1}. </Text>
              {line}
            </Text>
          ))}
          <Text style={local.example}>Exemple : {opening.rules.example}</Text>
        </View>
      ) : (
        <Text style={styles.helperText}>Chaque équipe entre sur le plateau avec sa touche de buzzer.</Text>
      )}
      <Pressable
        style={[styles.primaryButtonCompact, skipping && styles.primaryButtonDisabled]}
        onPress={() => skipOnce(onSkip)}
        disabled={skipping}
        accessibilityRole="button"
      >
        <Text style={styles.primaryButtonText}>{teams ? 'Passer aux règles' : 'Lancer la manche'}</Text>
      </Pressable>
    </View>
  );
}

const local = StyleSheet.create({
  card: { gap: 10, padding: 16, borderRadius: 14, borderWidth: 2, borderColor: colors.pink, backgroundColor: colors.hero },
  kicker: { color: colors.pink, fontFamily: fonts.display, fontSize: 15, textTransform: 'uppercase' },
  seconds: { color: colors.gold, fontFamily: fonts.display, fontSize: 22, fontVariant: ['tabular-nums'] },
  title: { color: colors.text, fontFamily: fonts.display, fontSize: 24, textTransform: 'uppercase' },
  rules: { gap: 6 },
  rule: { color: colors.text, fontFamily: fonts.bold, fontSize: 15, lineHeight: 21 },
  ruleIndex: { color: colors.gold, fontFamily: fonts.display },
  example: { color: colors.accent, fontFamily: fonts.bold, fontSize: 14, lineHeight: 20 },
});
