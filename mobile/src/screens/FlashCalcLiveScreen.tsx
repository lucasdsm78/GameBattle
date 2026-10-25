import { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';
import { RaceScoreCard, ScoreHighlight } from '../components/RaceScoreCard';
import { useSendLock } from '../hooks/useSendLock';
import { colors, styles } from '../theme';
import { FlashCalcState, FlashCalcVerdict, GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onBuzz: (team: string) => void;
  onPause: () => void;
  onResume: () => void;
  onBack: () => void;
};

const WARNING = '#f59e0b';

const verdictLabel = ({ team, correct, points }: FlashCalcVerdict): string => {
  if (correct) return `✓ ${team} +1`;
  return points < 0 ? `✕ ${team} −1` : `✕ ${team} reste à 0`;
};

const headline = (game: FlashCalcState): string => {
  switch (game.phase) {
    case 'running':
      return 'Juste ou faux ?';
    case 'feedback':
      return game.verdict ? verdictLabel(game.verdict) : 'Juste ou faux ?';
    case 'paused':
      return 'Défilement en pause';
    case 'finished':
      return `${game.winner_team} remporte la manche`;
    default:
      return 'Prêts à calculer ?';
  }
};

export function FlashCalcLiveScreen({ snapshot, errorMessage, onStart, onBuzz, onPause, onResume, onBack }: Props) {
  const game = snapshot.session.flash_calc;
  const teams = snapshot.settings.teams;
  const verdict = game.verdict;
  const scrolling = game.phase === 'running' || game.phase === 'feedback';
  const [controlling, controlOnce] = useSendLock(`${game.phase}-${game.calc_number}`);
  const highlight: ScoreHighlight = verdict ? { team: verdict.team, tone: verdict.correct ? 'good' : 'bad' } : null;

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Calcul flash · premier à {game.winning_score}</Text>
        <Text style={styles.title}>{headline(game)}</Text>
        {game.calc_number > 0 ? (
          <Text style={styles.subtitle}>
            Calcul n°{game.calc_number} · Niveau {game.level}/{game.max_level}
          </Text>
        ) : null}
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {game.phase === 'running' || verdict ? (
        <View style={[local.calcCard, verdict && (verdict.correct ? local.calcCardGood : local.calcCardBad)]}>
          <Text style={local.calcText} numberOfLines={1} adjustsFontSizeToFit accessibilityLiveRegion="polite">
            {verdict ? verdict.expression : game.expression} <Text style={local.equals}>=</Text>{' '}
            <Text style={!verdict ? local.result : verdict.correct ? local.resultJudged : local.struck}>
              {verdict ? verdict.shown_result : game.shown_result}
            </Text>
          </Text>
          {verdict && !verdict.correct ? (
            <Text style={local.correction}>
              C’était <Text style={local.resultJudged}>{verdict.true_result}</Text>
            </Text>
          ) : null}
          {game.phase === 'running' ? <CalcTimer key={game.calc_number} durationMs={game.deadline_ms - game.shown_at_ms} /> : null}
        </View>
      ) : null}

      {game.phase === 'idle' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.helperText}>
            Les calculs défilent seuls, de plus en plus vite. Les équipes buzzent uniquement quand le résultat est juste : +1 si
            c’est juste, −1 sinon (jamais sous 0). Le serveur arbitre, aucun présentateur n’est nécessaire.
          </Text>
          <Pressable
            style={[styles.primaryButton, controlling && styles.primaryButtonDisabled]}
            onPress={() => controlOnce(onStart)}
            disabled={controlling}
            accessibilityRole="button"
          >
            <Text style={styles.primaryButtonText}>▶ Lancer le défilement</Text>
          </Pressable>
        </View>
      ) : null}

      {game.phase === 'paused' ? (
        <Pressable
          style={[styles.primaryButton, controlling && styles.primaryButtonDisabled]}
          onPress={() => controlOnce(onResume)}
          disabled={controlling}
          accessibilityRole="button"
        >
          <Text style={styles.primaryButtonText}>▶ Reprendre</Text>
        </Pressable>
      ) : null}

      {scrolling ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Buzzers</Text>
          <View style={styles.scoreGrid}>
            {teams.map((team, index) => (
              <Pressable
                key={team}
                style={[styles.scoreTile, verdict?.team === team && styles.scoreTileActive]}
                onPress={() => onBuzz(team)}
                disabled={game.phase !== 'running'}
                accessibilityRole="button"
                accessibilityLabel={`Buzzer ${team}`}
              >
                <Text style={styles.scoreTileLabel}>{team}</Text>
                <Text style={styles.scoreTileHint}>Touche {snapshot.settings.buzzer_keys[index] ?? index + 1}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable style={styles.ghostButton} onPress={() => controlOnce(onPause)} disabled={controlling} accessibilityRole="button">
            <Text style={styles.ghostButtonText}>⏸ Mettre en pause</Text>
          </Pressable>
        </View>
      ) : null}

      <RaceScoreCard
        teams={teams}
        scores={game.scores}
        goal={game.winning_score}
        unit="point"
        highlight={highlight}
        winnerTeam={game.winner_team}
      />
    </>
  );
}

// Relancée à chaque calcul (clé) : la durée vient du serveur, l'animation tourne sur le thread natif.
function CalcTimer({ durationMs }: { durationMs: number }) {
  const progress = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const animation = Animated.timing(progress, {
      toValue: 0,
      duration: Math.max(0, durationMs),
      easing: Easing.linear,
      useNativeDriver: true,
    });
    animation.start();
    return () => animation.stop();
  }, [durationMs, progress]);

  return (
    <View style={local.timerTrack}>
      <Animated.View style={[local.timerFill, { transform: [{ scaleX: progress }] }]} />
    </View>
  );
}

const local = StyleSheet.create({
  calcCard: {
    gap: 16,
    paddingVertical: 26,
    paddingHorizontal: 18,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(245,158,11,0.4)',
    backgroundColor: '#17150f',
  },
  calcCardGood: { borderColor: colors.accent, backgroundColor: 'rgba(34,197,94,0.16)' },
  calcCardBad: { borderColor: colors.danger, backgroundColor: 'rgba(239,68,68,0.16)' },
  calcText: { color: colors.text, fontSize: 48, fontWeight: '900', textAlign: 'center', fontVariant: ['tabular-nums'] },
  equals: { color: colors.muted },
  result: { color: WARNING },
  resultJudged: { color: colors.accent },
  struck: { color: '#fca5a5', textDecorationLine: 'line-through' },
  correction: { color: colors.muted, fontSize: 20, fontWeight: '800', textAlign: 'center' },
  timerTrack: { height: 8, borderRadius: 999, overflow: 'hidden', backgroundColor: 'rgba(255,255,255,0.08)' },
  timerFill: { flex: 1, backgroundColor: WARNING, transformOrigin: 'left' },
});
