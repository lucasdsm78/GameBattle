import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { colors, styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onSelect: (team: string, targetCount: number) => void;
  onLaunch: () => void;
  onIncrement: () => void;
  onDecrement: () => void;
  onNextTheme: () => void;
  onBack: () => void;
};

export function AuctionLiveScreen({
  snapshot,
  errorMessage,
  onStart,
  onSelect,
  onLaunch,
  onIncrement,
  onDecrement,
  onNextTheme,
  onBack,
}: Props) {
  const game = snapshot.session.auction;
  const [bid, setBid] = useState('1');
  const [now, setNow] = useState(Date.now());
  const parsedBid = Number.parseInt(bid, 10);
  const validBid = Number.isInteger(parsedBid) && parsedBid >= 1 && parsedBid <= 100;

  useEffect(() => {
    if (game.phase !== 'running') return;
    setNow(Date.now());
    const tick = setInterval(() => setNow(Date.now()), 100);
    return () => {
      clearInterval(tick);
    };
  }, [game.deadline_at_ms, game.phase]);

  useEffect(() => {
    if (game.phase === 'bidding') setBid('1');
  }, [game.phase, game.theme_id]);

  const millisecondsLeft = game.phase === 'running' ? Math.max(0, game.deadline_at_ms - now) : 30_000;
  const secondsLeft = Math.ceil(millisecondsLeft / 1000);

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>L’Enchère · première équipe à 20</Text>
        <Text style={styles.title}>{game.prompt || 'Préparez la première enchère'}</Text>
        <Text style={styles.subtitle}>
          {game.phase === 'bidding' ? 'Les équipes annoncent leur mise. Sélectionnez la meilleure.' :
            game.phase === 'ready' ? `${game.active_team} doit donner ${game.target_count} réponses.` :
            game.phase === 'running' ? `${game.active_team} joue · ${secondsLeft}s restantes` :
            game.phase === 'resolved' ? (game.attempt_succeeded ? 'Enchère réussie !' : 'Enchère perdue : +2 aux adversaires.') :
            game.phase === 'finished' ? `Manche remportée par ${game.winner_team}` : 'Démarrez pour tirer un thème.'}
        </Text>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Scores</Text>
          <Text style={localStyles.goal}>Objectif 20</Text>
        </View>
        <View style={styles.scoreGrid}>
          {snapshot.settings.teams.map((team) => (
            <View key={team} style={[styles.scoreTile, game.active_team === team && styles.scoreTileActive]}>
              <Text style={styles.scoreTileLabel}>{team}</Text>
              <Text style={styles.scoreTileValue}>{game.scores[team] ?? 0}</Text>
              {game.points_awarded[team] ? <Text style={localStyles.points}>+{game.points_awarded[team]}</Text> : null}
            </View>
          ))}
        </View>
      </View>

      {game.phase === 'idle' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.helperText}>Un thème et sa liste de réponses seront tirés au sort.</Text>
          <Pressable style={styles.primaryButton} onPress={onStart}>
            <Text style={styles.primaryButtonText}>🎯 Lancer L’Enchère</Text>
          </Pressable>
        </View>
      ) : null}

      {game.phase === 'bidding' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Attribuer la plus haute enchère</Text>
          <Text style={styles.helperText}>Saisissez la meilleure enchère, puis sélectionnez l’équipe qui l’a annoncée.</Text>
          <TextInput
            style={[styles.input, localStyles.bidInput]}
            value={bid}
            onChangeText={setBid}
            keyboardType="number-pad"
            placeholder="Nombre de réponses"
            placeholderTextColor={colors.muted}
          />
          <Text style={styles.helperText}>Entre 1 et 100 réponses. La liste ci-dessous sert d’aide au présentateur.</Text>
          <View style={styles.actionRowWrap}>
            {snapshot.settings.teams.map((team) => (
              <Pressable
                key={team}
                style={[
                  localStyles.teamButton,
                  game.bidding_teams.includes(team) && localStyles.teamButtonBuzzed,
                  !validBid && styles.primaryButtonDisabled,
                ]}
                onPress={() => onSelect(team, parsedBid)}
                disabled={!validBid}
              >
                <Text style={localStyles.teamButtonName}>{team}</Text>
                <Text style={localStyles.teamButtonHint}>{game.bidding_teams.includes(team) ? '⚡ A buzzé' : 'Sélectionner'}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}

      {game.phase === 'ready' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>{game.active_team} · {game.target_count} réponses</Text>
          <Text style={styles.helperText}>L’équipe et l’objectif sont affichés sur le grand écran. Le chrono ne partira qu’au prochain appui.</Text>
          <Pressable style={styles.primaryButton} onPress={onLaunch}>
            <Text style={styles.primaryButtonText}>▶ C’est parti — 30 secondes</Text>
          </Pressable>
        </View>
      ) : null}

      {game.phase === 'running' ? (
        <View style={styles.sectionCard}>
          <Text style={[localStyles.timer, secondsLeft <= 5 && localStyles.timerDanger]}>{secondsLeft}s</Text>
          <Text style={localStyles.count}>{game.correct_count} / {game.target_count}</Text>
          <Pressable
            style={[styles.primaryButton, game.correct_count >= game.target_count && styles.primaryButtonDisabled]}
            onPress={onIncrement}
            disabled={game.correct_count >= game.target_count}
          >
            <Text style={styles.primaryButtonText}>+1 bonne réponse</Text>
          </Pressable>
          <Pressable
            style={[styles.ghostButton, game.correct_count <= 0 && styles.primaryButtonDisabled]}
            onPress={onDecrement}
            disabled={game.correct_count <= 0}
          >
            <Text style={styles.ghostButtonText}>−1 Corriger</Text>
          </Pressable>
          <Text style={styles.helperText}>Quand l’équipe a terminé, elle doit buzzer. À 0, la tentative est résolue automatiquement.</Text>
        </View>
      ) : null}

      {game.answers.length > 0 ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Réponses possibles · secret régie</Text>
          <View style={localStyles.answerGrid}>
            {game.answers.map((answer, index) => (
              <View key={`${answer}-${index}`} style={localStyles.answerRow}>
                <Text style={localStyles.answerIndex}>{index + 1}</Text>
                <Text style={localStyles.answerText}>{answer}</Text>
              </View>
            ))}
          </View>
        </View>
      ) : null}

      {game.phase === 'resolved' ? (
        <View style={styles.sectionCard}>
          <Text style={game.attempt_succeeded ? styles.winnerText : styles.errorText}>
            {game.attempt_succeeded
              ? `${game.active_team} remporte ${game.target_count} point${game.target_count > 1 ? 's' : ''}.`
              : `${game.active_team} échoue : chaque adversaire remporte 2 points.`}
          </Text>
          <Pressable style={styles.primaryButton} onPress={onNextTheme}>
            <Text style={styles.primaryButtonText}>Thème suivant →</Text>
          </Pressable>
        </View>
      ) : null}
    </>
  );
}

const localStyles = StyleSheet.create({
  goal: { color: colors.accent, fontWeight: '900' },
  points: { color: colors.accent, marginTop: 5, fontWeight: '800' },
  bidInput: { fontSize: 28, fontWeight: '900', textAlign: 'center' },
  teamButton: { flexBasis: '45%', flexGrow: 1, padding: 15, borderRadius: 16, backgroundColor: colors.cardAlt, borderWidth: 1, borderColor: colors.border },
  teamButtonBuzzed: { borderColor: colors.accent, backgroundColor: 'rgba(34,197,94,0.16)' },
  teamButtonName: { color: colors.text, fontWeight: '900', fontSize: 16 },
  teamButtonHint: { color: colors.muted, marginTop: 5 },
  timer: { color: colors.accent, fontSize: 54, fontWeight: '900', textAlign: 'center' },
  timerDanger: { color: colors.danger },
  count: { color: colors.text, fontSize: 44, fontWeight: '900', textAlign: 'center' },
  answerGrid: { gap: 8 },
  answerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: colors.cardAlt, padding: 11, borderRadius: 12 },
  answerIndex: { color: colors.accent, width: 28, textAlign: 'center', fontWeight: '900' },
  answerText: { color: colors.text, flex: 1, fontWeight: '700' },
});
