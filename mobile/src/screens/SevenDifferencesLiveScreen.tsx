import { useEffect, useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onOpen: () => void;
  onBuzz: (team: string) => void;
  onFound: (differenceId: string) => void;
  onReject: () => void;
  onBack: () => void;
};

export function SevenDifferencesLiveScreen({
  snapshot,
  errorMessage,
  onStart,
  onOpen,
  onBuzz,
  onFound,
  onReject,
  onBack,
}: Props) {
  const game = snapshot.session.seven_differences;
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (game.phase !== 'memorizing') return;
    const tick = setInterval(() => setNow(Date.now()), 200);
    const delay = Math.max(game.reveal_at_ms - Date.now(), 0);
    let retry: ReturnType<typeof setInterval> | undefined;
    const timer = setTimeout(() => {
      onOpen();
      retry = setInterval(onOpen, 1_000);
    }, delay);
    return () => {
      clearInterval(tick);
      clearTimeout(timer);
      if (retry) clearInterval(retry);
    };
  }, [game.phase, game.reveal_at_ms, onOpen]);

  const found = useMemo(() => new Set(game.found_difference_ids), [game.found_difference_ids]);
  const secondsLeft = Math.max(0, Math.ceil((game.reveal_at_ms - now) / 1000));
  const canValidate = game.phase === 'claimed' && Boolean(game.current_buzzer_team);

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Les 7 différences</Text>
        <Text style={styles.title}>{snapshot.settings.game_title}</Text>
        <Text style={styles.subtitle}>
          {game.phase === 'memorizing'
            ? `Mémorisation en cours · ${secondsLeft}s`
            : game.phase === 'claimed'
              ? `${game.current_buzzer_team} a la main`
              : game.phase === 'finished'
                ? 'Les 7 différences ont été trouvées'
                : 'En attente du premier buzz'}
        </Text>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {game.phase === 'idle' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Prêt pour l’observation ?</Text>
          <Text style={styles.helperText}>L’image originale sera affichée pendant exactement 25 secondes.</Text>
          <Pressable style={styles.primaryButton} onPress={onStart}>
            <Text style={styles.primaryButtonText}>👁️ Afficher l’image originale</Text>
          </Pressable>
        </View>
      ) : null}

      {game.phase !== 'idle' ? (
        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Score</Text>
            <Text style={localStyles.counter}>{7 - game.differences_remaining}/7</Text>
          </View>
          <View style={localStyles.teamGrid}>
            {snapshot.settings.teams.map((team) => (
              <Pressable
                key={team}
                style={[
                  localStyles.teamCard,
                  game.current_buzzer_team === team && localStyles.teamCardActive,
                  game.blocked_team === team && localStyles.teamCardBlocked,
                ]}
                onPress={() => onBuzz(team)}
                disabled={game.phase !== 'open' || game.blocked_team === team}
              >
                <Text style={localStyles.teamName}>{team}</Text>
                <Text style={localStyles.teamScore}>{game.scores[team] ?? 0}</Text>
                <Text style={localStyles.teamHint}>
                  {game.current_buzzer_team === team ? 'A la main' : game.blocked_team === team ? 'Temporairement bloquée' : 'Appuyer pour buzzer'}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}

      {game.differences.length ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Différences secrètes</Text>
          <Text style={styles.helperText}>Touchez la réponse annoncée uniquement si elle est correcte.</Text>
          {game.differences.map((difference, index) => {
            const isFound = found.has(difference.id);
            return (
              <Pressable
                key={difference.id}
                style={[localStyles.answer, isFound && localStyles.answerFound, (!canValidate || isFound) && styles.primaryButtonDisabled]}
                onPress={() => onFound(difference.id)}
                disabled={!canValidate || isFound}
              >
                <Text style={localStyles.answerNumber}>{isFound ? '✓' : index + 1}</Text>
                <Text style={[localStyles.answerText, isFound && localStyles.answerTextFound]}>{difference.label}</Text>
              </Pressable>
            );
          })}
          <Pressable
            style={[styles.primaryButton, styles.falseButton, !canValidate && styles.primaryButtonDisabled]}
            onPress={onReject}
            disabled={!canValidate}
          >
            <Text style={styles.primaryButtonText}>✕ Mauvaise réponse</Text>
          </Pressable>
        </View>
      ) : null}
    </>
  );
}

const localStyles = StyleSheet.create({
  counter: { color: colors.accent, fontSize: 24, fontWeight: '900' },
  teamGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  teamCard: { flexGrow: 1, flexBasis: '45%', padding: 14, borderRadius: 16, backgroundColor: colors.cardAlt, borderWidth: 1, borderColor: colors.border },
  teamCardActive: { borderColor: colors.accent, backgroundColor: 'rgba(34,197,94,0.18)' },
  teamCardBlocked: { borderColor: colors.danger, opacity: 0.55 },
  teamName: { color: colors.text, fontWeight: '800' },
  teamScore: { color: colors.accent, fontSize: 30, fontWeight: '900', marginVertical: 4 },
  teamHint: { color: colors.muted, fontSize: 12 },
  answer: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 14, backgroundColor: colors.cardAlt, borderWidth: 1, borderColor: colors.border },
  answerFound: { backgroundColor: 'rgba(34,197,94,0.14)', borderColor: colors.accent },
  answerNumber: { color: colors.accent, fontSize: 18, fontWeight: '900', width: 24, textAlign: 'center' },
  answerText: { color: colors.text, flex: 1, fontWeight: '700', lineHeight: 20 },
  answerTextFound: { color: colors.muted, textDecorationLine: 'line-through' },
});
