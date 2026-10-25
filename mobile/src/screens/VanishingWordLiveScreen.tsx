import { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';
import { useCountdown } from '../hooks/useCountdown';
import { useSendLock } from '../hooks/useSendLock';
import { useVolumeButtons } from '../hooks/useVolumeButtons';
import { colors, styles } from '../theme';
import { GameConfigSnapshot, VanishingWordState } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStartRound: () => void;
  onBuzz: (team: string) => void;
  onAnswer: (isCorrect: boolean) => void;
  onReveal: () => void;
  onBack: () => void;
};

const headline = (game: VanishingWordState): string => {
  switch (game.phase) {
    case 'memorizing':
      return 'Mémorisez la liste';
    case 'vanished':
      return 'Quel mot a disparu ?';
    case 'claimed':
      return `${game.current_buzzer_team} a la main`;
    case 'revealed':
      return game.round_winner ? `${game.round_winner} a trouvé !` : 'Personne n’a trouvé';
    case 'finished':
      return `${game.winner_team} remporte la manche`;
    default:
      return 'Prêts à mémoriser ?';
  }
};

export function VanishingWordLiveScreen({ snapshot, errorMessage, onStartRound, onBuzz, onAnswer, onReveal, onBack }: Props) {
  const game = snapshot.session.vanishing_word;
  const teams = snapshot.settings.teams;
  const claimed = game.phase === 'claimed';
  const hunting = game.phase === 'vanished' || claimed;
  const revealedToPresenter = Boolean(game.vanished_word);
  const [starting, startOnce] = useSendLock(`round-${game.round_number}`);
  const [judging, judgeOnce] = useSendLock(`judge-${game.round_number}-${game.current_buzzer_team}-${game.excluded_teams.length}`);

  const judge = (isCorrect: boolean) => judgeOnce(() => onAnswer(isCorrect));
  const volumeButtonsActive = useVolumeButtons({
    enabled: claimed,
    onVolumeUp: () => judge(true),
    onVolumeDown: () => judge(false),
  });

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Le mot qui disparaît · premier à {game.winning_score}</Text>
        <Text style={styles.title}>{headline(game)}</Text>
        {game.round_number > 0 ? <Text style={styles.subtitle}>Liste n°{game.round_number}</Text> : null}
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {game.phase === 'memorizing' ? <MemorizationTimer deadlineMs={game.reveal_at_ms} durationMs={game.memorization_ms} /> : null}

      {revealedToPresenter ? (
        <View style={local.answerCard}>
          <Text style={local.answerLabel}>Mot disparu · visible uniquement sur la régie</Text>
          <Text style={local.answerWord}>{game.vanished_word}</Text>
        </View>
      ) : null}

      {game.words.length ? (
        <View style={local.wordGrid}>
          {game.words.map((word) => {
            const vanished = word === game.vanished_word;
            return (
              <View key={word} style={[local.wordTile, vanished && local.wordTileVanished]}>
                <Text style={[local.word, vanished && local.wordVanished]} numberOfLines={1} adjustsFontSizeToFit>
                  {word}
                </Text>
                {vanished ? <Text style={local.vanishedTag}>A disparu</Text> : null}
              </View>
            );
          })}
        </View>
      ) : null}

      {game.phase === 'idle' || game.phase === 'revealed' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.helperText}>
            8 mots s’affichent pendant {Math.round(game.memorization_ms / 1000)} secondes, puis l’un d’eux disparaît.
          </Text>
          <Pressable
            style={[styles.primaryButton, starting && styles.primaryButtonDisabled]}
            onPress={() => startOnce(onStartRound)}
            disabled={starting}
            accessibilityRole="button"
          >
            <Text style={styles.primaryButtonText}>{game.phase === 'idle' ? '▶ Afficher la première liste' : 'Liste suivante →'}</Text>
          </Pressable>
        </View>
      ) : null}

      {hunting ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Buzzers</Text>
          <View style={styles.scoreGrid}>
            {teams.map((team, index) => {
              const excluded = game.excluded_teams.includes(team);
              const active = team === game.current_buzzer_team;
              return (
                <Pressable
                  key={team}
                  style={[styles.scoreTile, active && styles.scoreTileActive, excluded && local.excludedTile]}
                  onPress={() => onBuzz(team)}
                  disabled={excluded || claimed}
                >
                  <Text style={styles.scoreTileLabel}>{team}</Text>
                  <Text style={styles.scoreTileHint}>
                    {excluded ? 'S’est trompée' : active ? 'A la main' : `Touche ${snapshot.settings.buzzer_keys[index] ?? index + 1}`}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <View style={styles.actionRowWrap}>
            <Pressable
              style={[styles.primaryButtonCompact, styles.successButton, (!claimed || judging) && styles.primaryButtonDisabled]}
              onPress={() => judge(true)}
              disabled={!claimed || judging}
            >
              <Text style={styles.primaryButtonText}>✓ TROUVÉ (+1)</Text>
            </Pressable>
            <Pressable
              style={[styles.primaryButtonCompact, styles.falseButton, (!claimed || judging) && styles.primaryButtonDisabled]}
              onPress={() => judge(false)}
              disabled={!claimed || judging}
            >
              <Text style={styles.primaryButtonText}>✕ FAUX</Text>
            </Pressable>
          </View>
          <Pressable style={styles.ghostButton} onPress={onReveal}>
            <Text style={styles.ghostButtonText}>Révéler le mot sans point</Text>
          </Pressable>
          <Text style={styles.helperText}>
            {volumeButtonsActive ? '🔊 Volume + = TROUVÉ · 🔉 Volume − = FAUX' : 'Boutons volume inactifs (uniquement en APK).'}
          </Text>
        </View>
      ) : null}

      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Scores</Text>
          <Text style={local.goal}>Objectif {game.winning_score}</Text>
        </View>
        {teams.map((team) => {
          const score = game.scores[team] ?? 0;
          return (
            <View key={team} style={[styles.rankRow, team === game.winner_team && styles.rankRowWinner]}>
              <Text style={styles.rankTeam} numberOfLines={1}>{team}</Text>
              <View style={local.dots}>
                {Array.from({ length: game.winning_score }, (_, index) => (
                  <View key={index} style={[local.dot, index < score && local.dotFilled]} />
                ))}
              </View>
              <Text style={local.score}>{score}</Text>
            </View>
          );
        })}
      </View>
    </>
  );
}

type TimerProps = { deadlineMs: number; durationMs: number };

// Isolé pour que seul le compte à rebours se re-rende ; la barre est animée sur le thread natif.
function MemorizationTimer({ deadlineMs, durationMs }: TimerProps) {
  const seconds = Math.ceil(useCountdown(deadlineMs, true) / 1000);
  const progress = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const remainingMs = Math.max(0, deadlineMs - Date.now());
    progress.setValue(Math.min(1, remainingMs / durationMs));
    const animation = Animated.timing(progress, { toValue: 0, duration: remainingMs, easing: Easing.linear, useNativeDriver: true });
    animation.start();
    return () => animation.stop();
  }, [deadlineMs, durationMs, progress]);

  return (
    <View style={local.timer} accessibilityRole="timer" accessibilityLabel={`Disparition dans ${seconds} secondes`}>
      <View style={local.timerRow}>
        <Text style={local.timerLabel}>Un mot disparaît dans</Text>
        <Text style={local.timerValue}>{seconds}s</Text>
      </View>
      <View style={local.timerTrack}>
        <Animated.View style={[local.timerFill, { transform: [{ scaleX: progress }] }]} />
      </View>
    </View>
  );
}

const local = StyleSheet.create({
  timer: { gap: 8 },
  timerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  timerLabel: { color: colors.muted, fontWeight: '700', fontSize: 12, letterSpacing: 1.2, textTransform: 'uppercase' },
  timerValue: { color: colors.accent, fontSize: 30, fontWeight: '900', fontVariant: ['tabular-nums'] },
  timerTrack: { height: 8, borderRadius: 999, overflow: 'hidden', backgroundColor: 'rgba(255,255,255,0.08)' },
  timerFill: { flex: 1, backgroundColor: colors.accent, transformOrigin: 'left' },

  answerCard: {
    alignItems: 'center',
    gap: 6,
    padding: 18,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: 'rgba(239,68,68,0.45)',
    backgroundColor: '#1d1016',
  },
  answerLabel: { color: '#fca5a5', fontWeight: '800', fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase', textAlign: 'center' },
  answerWord: { color: colors.text, fontSize: 34, fontWeight: '900', textAlign: 'center' },

  wordGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  wordTile: {
    flexBasis: '47%',
    flexGrow: 1,
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 10,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.cardAlt,
  },
  wordTileVanished: { borderColor: colors.danger, backgroundColor: 'rgba(239,68,68,0.14)' },
  word: { color: colors.text, fontSize: 19, fontWeight: '800' },
  wordVanished: { color: '#fecaca' },
  vanishedTag: { color: '#fca5a5', fontSize: 11, fontWeight: '800', marginTop: 4, textTransform: 'uppercase' },
  excludedTile: { opacity: 0.4 },

  goal: { color: colors.accent, fontWeight: '900' },
  dots: { flexDirection: 'row', gap: 5 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: 'rgba(255,255,255,0.12)' },
  dotFilled: { backgroundColor: colors.accent },
  score: { color: colors.text, fontSize: 20, fontWeight: '900', minWidth: 24, textAlign: 'right', fontVariant: ['tabular-nums'] },
});
