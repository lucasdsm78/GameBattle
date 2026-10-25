import { ReactNode, useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';
import { RaceScoreCard, ScoreHighlight } from './RaceScoreCard';
import { useSendLock } from '../hooks/useSendLock';
import { colors, styles } from '../theme';
import { BuzzStreamGame, BuzzVerdict, GameConfigSnapshot } from '../types/gameConfig';

export const STREAM_WARNING = '#f59e0b';

type Props = {
  snapshot: GameConfigSnapshot;
  game: BuzzStreamGame;
  errorMessage: string | null;
  title: string;
  headlines: { idle: string; running: string; revealed: string };
  subtitle?: string;
  intro: string;
  // Identifie l'élément affiché : verrouille les boutons jusqu'à ce que l'état serveur avance.
  itemKey: string;
  // Carte de l'élément qui défile (ou du verdict) ; `null` quand rien n'est affiché.
  item: ReactNode;
  // Informations réservées à la régie (ex. la bonne réponse).
  presenterOnly?: ReactNode;
  onStart: () => void;
  onBuzz: (team: string) => void;
  onPause: () => void;
  onResume: () => void;
  onBack: () => void;
};

export const verdictLabel = ({ team, correct, points }: BuzzVerdict): string => {
  if (correct) return `✓ ${team} +1`;
  return points < 0 ? `✕ ${team} −1` : `✕ ${team} reste à 0`;
};

const headline = (game: BuzzStreamGame, headlines: Props['headlines']): string => {
  switch (game.phase) {
    case 'running':
      return headlines.running;
    case 'feedback':
      return game.verdict ? verdictLabel(game.verdict) : headlines.revealed;
    case 'paused':
      return game.auto_paused ? 'Pause automatique : personne ne joue ?' : 'Défilement en pause';
    case 'finished':
      return `${game.winner_team} remporte la manche`;
    default:
      return headlines.idle;
  }
};

// Écran régie commun des jeux « buzze seulement si… » : le serveur arbitre, la régie lance, met en pause
// et peut buzzer pour une équipe si un buzzer manque.
export function BuzzStreamScreen({
  snapshot,
  game,
  errorMessage,
  title,
  headlines,
  subtitle,
  intro,
  itemKey,
  item,
  presenterOnly,
  onStart,
  onBuzz,
  onPause,
  onResume,
  onBack,
}: Props) {
  const teams = snapshot.settings.teams;
  const { verdict } = game;
  const scrolling = game.phase === 'running' || game.phase === 'feedback';
  const [controlling, controlOnce] = useSendLock(`${game.phase}-${itemKey}`);
  const highlight: ScoreHighlight = verdict ? { team: verdict.team, tone: verdict.correct ? 'good' : 'bad' } : null;

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>
          {title} · premier à {game.winning_score}
        </Text>
        <Text style={styles.title}>{headline(game, headlines)}</Text>
        {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {presenterOnly}

      {item ? (
        <View style={[local.itemCard, verdict && (verdict.correct ? local.itemCardGood : local.itemCardBad)]}>{item}</View>
      ) : null}

      {game.phase === 'idle' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.helperText}>
            {intro} +1 si c’est juste, −1 sinon (jamais sous 0). Le serveur arbitre, aucun présentateur n’est nécessaire.
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
        <View style={styles.sectionCard}>
          {game.auto_paused ? (
            <Text style={styles.helperText}>
              Aucun buzz sur les {game.auto_pause_after} derniers éléments : le défilement s’est mis en pause tout seul.
            </Text>
          ) : null}
          <Pressable
            style={[styles.primaryButton, controlling && styles.primaryButtonDisabled]}
            onPress={() => controlOnce(onResume)}
            disabled={controlling}
            accessibilityRole="button"
          >
            <Text style={styles.primaryButtonText}>▶ Reprendre</Text>
          </Pressable>
        </View>
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

// Relancée à chaque élément (clé) : la durée vient du serveur, l'animation tourne sur le thread natif.
export function StreamTimer({ durationMs }: { durationMs: number }) {
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

export const streamStyles = StyleSheet.create({
  correction: { color: colors.muted, fontSize: 20, fontWeight: '800', textAlign: 'center' },
  good: { color: colors.accent },
});

const local = StyleSheet.create({
  itemCard: {
    gap: 16,
    alignItems: 'stretch',
    paddingVertical: 26,
    paddingHorizontal: 18,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(245,158,11,0.4)',
    backgroundColor: '#17150f',
  },
  itemCardGood: { borderColor: colors.accent, backgroundColor: 'rgba(34,197,94,0.16)' },
  itemCardBad: { borderColor: colors.danger, backgroundColor: 'rgba(239,68,68,0.16)' },
  timerTrack: { height: 8, borderRadius: 999, overflow: 'hidden', backgroundColor: 'rgba(255,255,255,0.08)' },
  timerFill: { flex: 1, backgroundColor: STREAM_WARNING, transformOrigin: 'left' },
});
