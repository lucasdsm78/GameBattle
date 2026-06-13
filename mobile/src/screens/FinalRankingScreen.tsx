import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  onRevealNext: () => void;
  onBack: () => void;
};

export function FinalRankingScreen({ snapshot, onRevealNext, onBack }: Props) {
  const session = snapshot.session;
  // final_ranking est ordonné du dernier au 1er (révélation). On inverse l'affichage pour mettre
  // le meilleur révélé en haut et le dernier tout en bas.
  const revealed = session.final_ranking.slice(0, session.ranking_reveal_count).reverse();
  const allRevealed = session.ranking_reveal_count >= session.final_ranking_total && session.final_ranking_total > 0;

  return (
    <>
      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Partie terminée</Text>
        <Text style={styles.title}>Classement final</Text>
        <Text style={styles.helperText}>
          {session.total_rounds} manches jouées. Appuie sur « Suivant » pour révéler chaque équipe, du dernier au premier.
        </Text>
      </View>

      <View style={styles.sectionCard}>
        {revealed.length === 0 ? (
          <Text style={styles.helperText}>Appuie sur « Suivant » pour démarrer la révélation…</Text>
        ) : null}
        {revealed.map((entry) => (
          <View key={entry.team} style={[styles.rankRow, entry.rank === 1 && styles.rankRowWinner]}>
            <Text style={styles.rankPosition}>{entry.rank}{entry.rank === 1 ? 'er' : 'e'}</Text>
            <Text style={styles.rankTeam}>{entry.team}</Text>
            <Text style={styles.rankScore}>
              {entry.manches_won} manche{entry.manches_won > 1 ? 's' : ''}
            </Text>
          </View>
        ))}
      </View>

      {!allRevealed ? (
        <Pressable style={styles.primaryButton} onPress={onRevealNext}>
          <Text style={styles.primaryButtonText}>Suivant</Text>
        </Pressable>
      ) : (
        <Pressable style={styles.primaryButton} onPress={onBack}>
          <Text style={styles.primaryButtonText}>Nouvelle partie</Text>
        </Pressable>
      )}
    </>
  );
}
