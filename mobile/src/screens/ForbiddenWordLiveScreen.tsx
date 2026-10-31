import { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, StyleSheet, Text, View } from 'react-native';
import { useKeepAwake } from 'expo-keep-awake';
import { useCountdown } from '../hooks/useCountdown';
import { useSendLock } from '../hooks/useSendLock';
import { useVolumeButtons } from '../hooks/useVolumeButtons';
import { colors, styles, fonts } from '../theme';
import { ForbiddenWordCard, ForbiddenWordState, ForbiddenWordTurn, GameConfigSnapshot } from '../types/gameConfig';

const DANGER_SECONDS = 10;

const words = (count: number) => `${count} mot${count > 1 ? 's' : ''}`;

type ScreenProps = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStartTurn: () => void;
  onBack: () => void;
};

export function ForbiddenWordLiveScreen({ snapshot, errorMessage, onStartTurn, onBack }: ScreenProps) {
  const game = snapshot.session.forbidden_word;
  const [starting, startOnce] = useSendLock(`turn-${game.turns.length}`);

  if (game.phase === 'running' && game.current_card) {
    return <RunningTurn game={game} card={game.current_card} errorMessage={errorMessage} />;
  }

  const lastTurn = game.turns.at(-1);
  const finished = game.phase === 'finished';
  const suddenDeath = game.sudden_death_round > 0;
  const seconds = Math.round(game.turn_duration_ms / 1000);

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={[styles.eyebrow, suddenDeath && !finished && local.suddenDeath]}>
          {suddenDeath && !finished ? `Mort subite · ${seconds} s par équipe` : 'Le mot interdit · 60 s par équipe'}
        </Text>
        <Text style={styles.title}>
          {finished
            ? game.winner_team === 'Égalité' ? 'Égalité !' : `${game.winner_team} remporte la manche`
            : `Au tour de ${game.current_team}`}
        </Text>
        <Text style={styles.subtitle}>
          {finished
            ? 'Toutes les équipes ont joué.'
            : suddenDeath
              ? `Égalité entre ${game.sudden_death_teams.join(' et ')} : le plus de mots en ${seconds} secondes l’emporte.`
              : 'Faites deviner un maximum de mots à votre équipe sans prononcer les mots interdits.'}
        </Text>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {lastTurn ? <TurnRecap turn={lastTurn} /> : null}

      {game.phase === 'ready' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Passez le téléphone à l’orateur</Text>
          <Text style={styles.helperText}>
            Seul l’orateur voit le mot et ses mots interdits. Son équipe devine en regardant le grand écran.
          </Text>
          <Pressable
            style={[styles.primaryButton, starting && styles.primaryButtonDisabled]}
            onPress={() => startOnce(onStartTurn)}
            disabled={starting}
            accessibilityRole="button"
          >
            <Text style={styles.primaryButtonText}>▶ C’est parti — {seconds} secondes</Text>
          </Pressable>
          <Text style={styles.helperText}>Pendant le tour : TROUVÉ ou Volume + · PASSER ou Volume −</Text>
        </View>
      ) : null}

      <Scoreboard game={game} />
    </>
  );
}

type RunningTurnProps = {
  game: ForbiddenWordState;
  card: ForbiddenWordCard;
  errorMessage: string | null;
};

function RunningTurn({ game, card, errorMessage }: RunningTurnProps) {
  const foundCount = game.turns.at(-1)?.found_words.length ?? 0;

  return (
    <>
      <View style={local.turnHeader}>
        <View style={local.teamPill}>
          <Text style={local.teamPillText} numberOfLines={1}>{game.current_team}</Text>
        </View>
        <Text style={local.tally}>✓ {words(foundCount)}</Text>
      </View>

      <TurnTimer deadlineMs={game.deadline_at_ms} durationMs={game.turn_duration_ms} />

      <View style={local.wordCard} accessibilityLabel={`Mot à faire deviner : ${card.word}`}>
        <Text style={local.cardLabel}>Faites deviner</Text>
        <Text style={local.word} numberOfLines={2} adjustsFontSizeToFit minimumFontScale={0.6}>
          {card.word}
        </Text>
      </View>

      <View style={local.forbiddenCard}>
        <Text style={[local.cardLabel, local.forbiddenLabel]}>Mots interdits</Text>
        {card.forbidden_words.map((forbidden) => (
          <View key={forbidden} style={local.forbiddenRow}>
            <Text style={local.forbiddenWord} numberOfLines={1} adjustsFontSizeToFit>
              {forbidden}
            </Text>
          </View>
        ))}
      </View>

      {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
    </>
  );
}

type TurnTimerProps = { deadlineMs: number; durationMs: number };

// Isolé pour que seul le chrono se re-rende ; la barre est animée sur le thread natif.
function TurnTimer({ deadlineMs, durationMs }: TurnTimerProps) {
  const seconds = Math.ceil(useCountdown(deadlineMs, true) / 1000);
  const progress = useRef(new Animated.Value(1)).current;
  const danger = seconds <= DANGER_SECONDS;

  useEffect(() => {
    const remainingMs = Math.max(0, deadlineMs - Date.now());
    progress.setValue(Math.min(1, remainingMs / durationMs));
    const animation = Animated.timing(progress, {
      toValue: 0,
      duration: remainingMs,
      easing: Easing.linear,
      useNativeDriver: true,
    });
    animation.start();
    return () => animation.stop();
  }, [deadlineMs, durationMs, progress]);

  return (
    <View style={local.timer} accessibilityRole="timer" accessibilityLabel={`${seconds} secondes restantes`}>
      <View style={local.timerRow}>
        <Text style={local.timerLabel}>Temps restant</Text>
        <Text style={[local.timerValue, danger && local.dangerText]}>{seconds}s</Text>
      </View>
      <View style={local.timerTrack}>
        <Animated.View style={[local.timerFill, danger && local.timerFillDanger, { transform: [{ scaleX: progress }] }]} />
      </View>
    </View>
  );
}

function TurnRecap({ turn }: { turn: ForbiddenWordTurn }) {
  const hasWords = turn.found_words.length + turn.skipped_words.length > 0;
  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeader}>
        <Text style={[styles.sectionTitle, local.shrink]} numberOfLines={1}>{turn.team}</Text>
        <Text style={local.recapCount}>{words(turn.found_words.length)}</Text>
      </View>
      {hasWords ? (
        <View style={local.chipRow}>
          {turn.found_words.map((word) => (
            <Text key={`found-${word}`} style={[local.chip, local.chipFound]}>✓ {word}</Text>
          ))}
          {turn.skipped_words.map((word) => (
            <Text key={`skipped-${word}`} style={[local.chip, local.chipSkipped]}>{word}</Text>
          ))}
        </View>
      ) : (
        <Text style={styles.helperText}>Aucun mot sur ce tour.</Text>
      )}
    </View>
  );
}

function Scoreboard({ game }: { game: ForbiddenWordState }) {
  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Tableau des scores</Text>
        <Text style={local.mutedLabel}>Ordre de passage</Text>
      </View>
      {game.turn_order.map((team, index) => {
        const suddenDeath = game.sudden_death_round > 0;
        const played = suddenDeath || game.turns.some((turn) => turn.team === team && turn.round === game.sudden_death_round);
        const out = suddenDeath && !game.sudden_death_teams.includes(team);
        const highlighted = team === game.current_team || team === game.winner_team;
        return (
          <View key={team} style={[styles.rankRow, highlighted && styles.rankRowWinner, out && local.outRow]}>
            <Text style={styles.rankPosition}>{index + 1}</Text>
            <Text style={styles.rankTeam} numberOfLines={1}>{team}</Text>
            <Text style={played ? local.score : styles.rankScore}>
              {played ? game.scores[team] ?? 0 : team === game.current_team ? 'À vous' : 'À venir'}
            </Text>
          </View>
        );
      })}
    </View>
  );
}

type ActionBarProps = {
  cardId: string;
  onFound: (cardId: string) => void;
  onSkip: (cardId: string) => void;
};

// Barre fixe hors ScrollView : TROUVÉ / PASSER restent sous le pouce pendant toute la minute.
export function ForbiddenWordActionBar({ cardId, onFound, onSkip }: ActionBarProps) {
  useKeepAwake();
  const [locked, sendOnce] = useSendLock(cardId);
  const found = () => sendOnce(() => onFound(cardId));
  const skip = () => sendOnce(() => onSkip(cardId));
  const volumeButtonsActive = useVolumeButtons({ enabled: true, onVolumeUp: found, onVolumeDown: skip });

  return (
    <View style={local.actionBar}>
      <Pressable
        style={({ pressed }) => [local.skipButton, pressed && local.pressed, locked && styles.primaryButtonDisabled]}
        onPress={skip}
        disabled={locked}
        accessibilityRole="button"
        accessibilityLabel="Passer ce mot"
      >
        <Text style={local.skipText}>↷ Passer</Text>
        <Text style={local.skipHint}>{volumeButtonsActive ? 'Volume −' : 'Sans point'}</Text>
      </Pressable>
      <Pressable
        style={({ pressed }) => [local.foundButton, pressed && local.pressed, locked && styles.primaryButtonDisabled]}
        onPress={found}
        disabled={locked}
        accessibilityRole="button"
        accessibilityLabel="Mot trouvé"
      >
        <Text style={local.foundText}>✓ TROUVÉ</Text>
        <Text style={local.foundHint}>{volumeButtonsActive ? 'ou Volume +' : '+1 point'}</Text>
      </Pressable>
    </View>
  );
}

const local = StyleSheet.create({
  shrink: { flexShrink: 1 },
  suddenDeath: { color: colors.danger },
  outRow: { opacity: 0.4 },
  turnHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  teamPill: { flexShrink: 1, backgroundColor: colors.gold, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8 },
  teamPillText: { color: colors.ink, fontFamily: fonts.black, fontSize: 15 },
  tally: { color: colors.text, fontFamily: fonts.black, fontSize: 18 },

  timer: { gap: 8 },
  timerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  timerLabel: { color: colors.muted, fontFamily: fonts.bold, fontSize: 12, letterSpacing: 1.2, textTransform: 'uppercase' },
  timerValue: { color: colors.gold, fontSize: 34, fontFamily: fonts.black, fontVariant: ['tabular-nums'] },
  dangerText: { color: colors.danger },
  timerTrack: { height: 8, borderRadius: 999, overflow: 'hidden', backgroundColor: 'rgba(255,255,255,0.08)' },
  timerFill: { flex: 1, backgroundColor: colors.gold, transformOrigin: 'left' },
  timerFillDanger: { backgroundColor: colors.danger },

  cardLabel: { color: colors.gold, fontFamily: fonts.black, fontSize: 12, letterSpacing: 1.5, textTransform: 'uppercase' },
  wordCard: {
    alignItems: 'center',
    gap: 10,
    paddingVertical: 30,
    paddingHorizontal: 20,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(255,198,41,0.45)',
    backgroundColor: colors.hero,
  },
  word: { color: colors.text, fontSize: 44, lineHeight: 52, fontFamily: fonts.black, textAlign: 'center' },
  forbiddenCard: {
    gap: 10,
    padding: 16,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(255,61,94,0.4)',
    backgroundColor: '#1d1016',
  },
  forbiddenLabel: { color: '#fca5a5' },
  forbiddenRow: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderLeftWidth: 4,
    borderLeftColor: colors.danger,
    backgroundColor: 'rgba(255,61,94,0.12)',
  },
  forbiddenWord: { color: '#fecaca', fontSize: 21, fontFamily: fonts.black },

  recapCount: { color: colors.gold, fontSize: 20, fontFamily: fonts.black },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { overflow: 'hidden', paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, fontFamily: fonts.black },
  chipFound: { color: '#b6ffd2', backgroundColor: 'rgba(34,221,107,0.16)' },
  chipSkipped: { color: colors.muted, backgroundColor: 'rgba(255,255,255,0.06)', textDecorationLine: 'line-through' },
  mutedLabel: { color: colors.muted, fontFamily: fonts.bold, fontSize: 12 },
  score: { color: colors.text, fontSize: 22, fontFamily: fonts.black, fontVariant: ['tabular-nums'] },

  actionBar: {
    flexShrink: 0,
    flexDirection: 'row',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 16,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,198,41,0.35)',
    backgroundColor: colors.card,
  },
  foundButton: { flex: 2, minHeight: 92, alignItems: 'center', justifyContent: 'center', gap: 4, borderRadius: 22, backgroundColor: colors.accent },
  foundText: { color: colors.ink, fontSize: 26, fontFamily: fonts.black, letterSpacing: 1 },
  foundHint: { color: 'rgba(4,16,25,0.7)', fontSize: 12, fontFamily: fonts.black },
  skipButton: {
    flex: 1,
    minHeight: 92,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.cardAlt,
  },
  skipText: { color: colors.text, fontSize: 18, fontFamily: fonts.black },
  skipHint: { color: colors.muted, fontSize: 12, fontFamily: fonts.bold },
  pressed: { opacity: 0.85, transform: [{ scale: 0.97 }] },
});
