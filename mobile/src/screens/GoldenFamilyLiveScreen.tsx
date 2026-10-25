import { Pressable, StyleSheet, Text, View } from 'react-native';
import { RaceScoreCard } from '../components/RaceScoreCard';
import { useSendLock } from '../hooks/useSendLock';
import { useVolumeButtons } from '../hooks/useVolumeButtons';
import { colors, styles } from '../theme';
import { GameConfigSnapshot, GoldenFamilyState } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onNextQuestion: () => void;
  onBuzz: (team: string) => void;
  onAnswer: (answerIndex: number, turn: number) => void;
  onStrike: (turn: number) => void;
  onRevealBoard: () => void;
  onBack: () => void;
};

const GOLD = '#fbbf24';
const ANSWERING = new Set<GoldenFamilyState['phase']>(['duel', 'control', 'steal']);
const QUESTION_ACTIVE = new Set<GoldenFamilyState['phase']>(['faceoff', 'duel', 'control', 'steal']);

const headline = (game: GoldenFamilyState): string => {
  switch (game.phase) {
    case 'faceoff':
      return 'Face-à-face : buzzez !';
    case 'duel':
      return `Face-à-face · ${game.current_team} répond`;
    case 'control':
      return `${game.control_team} a la main`;
    case 'steal':
      return game.current_team === game.steal_from
        ? `La main revient à ${game.current_team}`
        : `${game.current_team} tente de prendre la main`;
    case 'revealed':
      return 'Question terminée';
    case 'finished':
      return `${game.winner_team} remporte la manche`;
    default:
      return 'Prêts pour Une famille en or ?';
  }
};

const turnHint = (game: GoldenFamilyState): string => {
  if (game.phase === 'duel') return 'La réponse la plus citée du face-à-face prend la main.';
  if (game.phase === 'control') return `${game.strikes}/${game.max_strikes} faute${game.strikes > 1 ? 's' : ''} · touchez la réponse donnée, sinon FAUTE.`;
  if (game.phase === 'steal') return 'Une seule réponse : la meilleure reprend la main.';
  return '';
};

export function GoldenFamilyLiveScreen({ snapshot, errorMessage, onNextQuestion, onBuzz, onAnswer, onStrike, onRevealBoard, onBack }: Props) {
  const game = snapshot.session.golden_family;
  const teams = snapshot.settings.teams;
  const answering = ANSWERING.has(game.phase) && game.current_team !== null;
  // Un appui par tour : le serveur ignore de toute façon une décision rejouée (même `turn`).
  const [judging, judgeOnce] = useSendLock(`turn-${game.question_number}-${game.turn}`);
  const [advancing, advanceOnce] = useSendLock(`question-${game.question_number}-${game.phase}`);

  const strike = () => judgeOnce(() => onStrike(game.turn));
  const volumeButtonsActive = useVolumeButtons({ enabled: answering, onVolumeUp: () => undefined, onVolumeDown: strike });

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={[styles.eyebrow, local.gold]}>Une famille en or · premier à {game.winning_score}</Text>
        <Text style={styles.title}>{headline(game)}</Text>
        {game.question ? <Text style={local.question}>{game.question.text}</Text> : null}
        {turnHint(game) ? <Text style={styles.subtitle}>{turnHint(game)}</Text> : null}
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {game.question && game.phase !== 'idle' ? (
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Réponses</Text>
            <View style={local.strikes} accessibilityLabel={`${game.strikes} fautes sur ${game.max_strikes}`}>
              {Array.from({ length: game.max_strikes }, (_, index) => (
                <Text key={index} style={[local.strike, index < game.strikes && local.strikeOn]}>
                  ✕
                </Text>
              ))}
            </View>
          </View>
          {game.question.answers.map((answer, index) => {
            const slot = game.board[index];
            const selectable = answering && !slot?.revealed && !judging;
            return (
              <Pressable
                key={answer.text}
                style={[local.answer, slot?.revealed && local.answerRevealed, selectable && local.answerSelectable]}
                onPress={() => judgeOnce(() => onAnswer(index, game.turn))}
                disabled={!selectable}
                accessibilityRole="button"
                accessibilityLabel={`${answer.text}, ${answer.points} points`}
                accessibilityState={{ disabled: !selectable }}
              >
                <Text style={local.answerRank}>{index + 1}</Text>
                <View style={local.answerBody}>
                  <Text style={[local.answerText, slot?.revealed && local.answerTextRevealed]} numberOfLines={2}>
                    {answer.text}
                  </Text>
                  {slot?.revealed ? (
                    <Text style={local.answerFoundBy}>{slot.found_by ? `✓ ${slot.found_by}` : 'Révélée'}</Text>
                  ) : null}
                </View>
                <Text style={local.answerPoints}>{answer.points}</Text>
              </Pressable>
            );
          })}

          {answering ? (
            <>
              <Pressable
                style={[styles.primaryButton, styles.falseButton, judging && styles.primaryButtonDisabled]}
                onPress={strike}
                disabled={judging}
                accessibilityRole="button"
              >
                <Text style={styles.primaryButtonText}>✕ FAUTE · {game.current_team}</Text>
              </Pressable>
              <Text style={styles.helperText}>
                {volumeButtonsActive ? '🔉 Volume − = FAUTE' : 'Bouton volume inactif (uniquement en APK).'}
              </Text>
            </>
          ) : null}
        </View>
      ) : null}

      {game.phase === 'faceoff' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Buzzers</Text>
          <View style={styles.scoreGrid}>
            {teams.map((team, index) => (
              <Pressable key={team} style={styles.scoreTile} onPress={() => onBuzz(team)} accessibilityRole="button">
                <Text style={styles.scoreTileLabel}>{team}</Text>
                <Text style={styles.scoreTileHint}>Touche {snapshot.settings.buzzer_keys[index] ?? index + 1}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}

      {game.phase === 'idle' || game.phase === 'revealed' ? (
        <Pressable
          style={[styles.primaryButton, local.goldButton, advancing && styles.primaryButtonDisabled]}
          onPress={() => advanceOnce(onNextQuestion)}
          disabled={advancing}
          accessibilityRole="button"
        >
          <Text style={local.goldButtonText}>{game.phase === 'idle' ? '▶ Première question' : 'Question suivante →'}</Text>
        </Pressable>
      ) : null}

      {QUESTION_ACTIVE.has(game.phase) ? (
        <Pressable style={styles.ghostButton} onPress={() => advanceOnce(onRevealBoard)} disabled={advancing} accessibilityRole="button">
          <Text style={styles.ghostButtonText}>Révéler les réponses restantes (sans points)</Text>
        </Pressable>
      ) : null}

      <RaceScoreCard
        teams={teams}
        scores={game.scores}
        goal={game.winning_score}
        unit="point"
        highlight={game.current_team ? { team: game.current_team, tone: 'good' } : null}
        winnerTeam={game.winner_team}
      />
    </>
  );
}

const local = StyleSheet.create({
  gold: { color: GOLD },
  question: { color: colors.text, fontSize: 18, fontWeight: '700', marginTop: 10, lineHeight: 24 },
  strikes: { flexDirection: 'row', gap: 6 },
  strike: { color: 'rgba(239,68,68,0.3)', fontSize: 22, fontWeight: '900' },
  strikeOn: { color: colors.danger },
  answer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    minHeight: 56,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.cardAlt,
  },
  answerSelectable: { borderColor: 'rgba(251,191,36,0.6)', backgroundColor: '#1b2335' },
  answerRevealed: { borderColor: 'rgba(34,197,94,0.45)', backgroundColor: 'rgba(34,197,94,0.1)' },
  answerRank: {
    width: 30,
    height: 30,
    borderRadius: 15,
    overflow: 'hidden',
    textAlign: 'center',
    textAlignVertical: 'center',
    lineHeight: 30,
    color: '#1c1300',
    backgroundColor: GOLD,
    fontWeight: '900',
  },
  answerBody: { flex: 1, gap: 2 },
  answerText: { color: colors.text, fontSize: 17, fontWeight: '800' },
  answerTextRevealed: { color: '#bbf7d0' },
  answerFoundBy: { color: colors.muted, fontSize: 12, fontWeight: '700' },
  answerPoints: { color: GOLD, fontSize: 22, fontWeight: '900', minWidth: 34, textAlign: 'right', fontVariant: ['tabular-nums'] },
  goldButton: { backgroundColor: GOLD },
  goldButtonText: { color: '#1c1300', fontWeight: '900', fontSize: 16, textAlign: 'center' },
});
