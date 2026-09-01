import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onBack: () => void;
};

export function MemoryLiveScreen({
  snapshot,
  errorMessage,
  onStart,
  onBack,
}: Props) {
  const memory = snapshot.session.memory;
  const teams = snapshot.settings.teams;
  const currentTeam = teams[memory.current_team_index] ?? '—';
  const qualified = new Set(memory.qualified_team_indices);

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Mémoire en chaîne</Text>
        <Text style={styles.title}>{snapshot.settings.game_title}</Text>
        <Text style={styles.subtitle}>Chaque équipe mémorise sa propre chaîne de 8 réponses, puis la récite dans l’ordre.</Text>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {memory.phase === 'idle' ? (
        <View style={styles.memoryCard}>
          <Text style={styles.memoryInstruction}>Une équipe de départ sera tirée au hasard.</Text>
          <Pressable style={styles.primaryButton} onPress={onStart}>
            <Text style={styles.primaryButtonText}>🧠 Commencer</Text>
          </Pressable>
        </View>
      ) : null}

      {memory.phase === 'question' && memory.current_question ? (
        <>
          <View style={styles.memoryCard}>
            <Text style={styles.nowPlayingLabel}>Question {memory.turn_number}/{memory.chain_length} · {currentTeam}</Text>
            <Text style={styles.questionText}>{memory.current_question.question}</Text>
            <View style={styles.answerCard}>
              <Text style={styles.nowPlayingLabel}>Réponse attendue</Text>
              <Text style={styles.answerText}>{memory.current_question.answer}</Text>
            </View>
          </View>
        </>
      ) : null}

      {memory.phase === 'question' || memory.phase === 'recitation' ? (
        <>
          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Chaîne de {currentTeam} · {memory.sequence_length}/{memory.chain_length}</Text>
            {memory.validated_answers.length ? memory.validated_answers.map((answer, index) => (
              <View key={`${index}-${answer}`} style={styles.memoryAnswerRow}>
                <Text style={styles.memoryAnswerIndex}>{index + 1}</Text>
                <Text style={styles.memoryAnswerText}>{answer}</Text>
              </View>
            )) : <Text style={styles.helperText}>La chaîne de cette équipe est vide.</Text>}
          </View>

          {memory.phase === 'recitation' ? (
            <View style={styles.sectionCard}>
              <Text style={styles.sectionTitle}>🎙 {currentTeam} récite maintenant les 8 réponses</Text>
              <Text style={styles.helperText}>Vérifiez que toutes les réponses sont données dans l’ordre exact.</Text>
            </View>
          ) : null}
        </>
      ) : null}

      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Équipes</Text>
        <View style={styles.scoreGrid}>
          {teams.map((team, index) => (
            <View key={team} style={[styles.scoreTile, qualified.has(index) && styles.scoreTileActive]}>
              <Text style={styles.scoreTileLabel}>{team}</Text>
              <Text style={styles.scoreTileHint}>
                {memory.phase === 'idle' ? 'En attente' : qualified.has(index) ? 'Qualifiée' : 'Disqualifiée'}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {memory.phase === 'finished' ? (
        <View style={styles.memoryCard}>
          <Text style={styles.memoryWinner}>🏆 {memory.winner_team}</Text>
          <Text style={styles.memoryInstruction}>Dernière équipe encore qualifiée</Text>
        </View>
      ) : null}
    </>
  );
}
