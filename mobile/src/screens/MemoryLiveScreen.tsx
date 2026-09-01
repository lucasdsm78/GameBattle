import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onValidate: () => void;
  onDisqualify: () => void;
  onBack: () => void;
};

export function MemoryLiveScreen({ snapshot, errorMessage, onStart, onValidate, onDisqualify, onBack }: Props) {
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
        <Text style={styles.subtitle}>Récitez toutes les réponses dans l’ordre, puis répondez à la nouvelle question.</Text>
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
            <Text style={styles.nowPlayingLabel}>Tour {memory.turn_number} · À {currentTeam}</Text>
            <Text style={styles.questionText}>{memory.current_question.question}</Text>
            <View style={styles.answerCard}>
              <Text style={styles.nowPlayingLabel}>Réponse attendue</Text>
              <Text style={styles.answerText}>{memory.current_question.answer}</Text>
            </View>
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Chaîne à réciter dans l’ordre</Text>
            {memory.validated_answers.length ? memory.validated_answers.map((answer, index) => (
              <View key={`${index}-${answer}`} style={styles.memoryAnswerRow}>
                <Text style={styles.memoryAnswerIndex}>{index + 1}</Text>
                <Text style={styles.memoryAnswerText}>{answer}</Text>
              </View>
            )) : <Text style={styles.helperText}>La chaîne est vide : répondez seulement à la question actuelle.</Text>}
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Arbitrage</Text>
            <Pressable style={styles.primaryButton} onPress={onValidate}>
              <Text style={styles.primaryButtonText}>✓ Séquence et réponse correctes</Text>
            </Pressable>
            <Pressable style={[styles.primaryButton, styles.falseButton]} onPress={onDisqualify}>
              <Text style={styles.primaryButtonText}>✕ Faute — disqualifier {currentTeam}</Text>
            </Pressable>
          </View>
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
