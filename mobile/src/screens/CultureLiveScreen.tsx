import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';
import { useVolumeButtons } from '../hooks/useVolumeButtons';

type CultureDifficultyChoice = 'facile' | 'moyen' | 'difficile';
const DIFFICULTY_CHOICES: { key: CultureDifficultyChoice; label: string }[] = [
  { key: 'facile', label: 'Facile' },
  { key: 'moyen', label: 'Moyen' },
  { key: 'difficile', label: 'Difficile' },
];

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onSelectDifficulty: (difficulty: CultureDifficultyChoice) => void;
  onBuzz: (team: string) => void;
  onAnswer: (isCorrect: boolean) => void;
  onNext: () => void;
  onBack: () => void;
};

export function CultureLiveScreen({
  snapshot,
  errorMessage,
  onStart,
  onSelectDifficulty,
  onBuzz,
  onAnswer,
  onNext,
  onBack,
}: Props) {
  const culture = snapshot.session.culture;
  const teams = snapshot.settings.teams;
  const buzzerKeys = snapshot.settings.buzzer_keys;
  const question = culture.current_question;
  const total = Math.max(culture.total_questions, 1);

  // Une équipe a buzzé et attend la validation (réponse pas encore validée).
  const answerPending = Boolean(culture.current_buzzer_team) && !culture.answered;
  const canGoNext = culture.phase === 'question' && culture.answered;

  // Boutons volume physiques (APK) : haut = Vrai si buzz en attente, puis question suivante après révélation ; bas = Faux.
  const volumeButtonsActive = useVolumeButtons({
    enabled: culture.phase === 'question',
    onVolumeUp: () => {
      if (answerPending) {
        onAnswer(true);
      } else if (canGoNext) {
        onNext();
      }
    },
    onVolumeDown: () => {
      if (answerPending) {
        onAnswer(false);
      }
    },
  });

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer la partie</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Culture générale</Text>
        <Text style={styles.title}>{snapshot.settings.game_title}</Text>
        <View style={styles.badgeRow}>
          {culture.phase === 'question' ? (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>Question {culture.current_index}/{total}</Text>
            </View>
          ) : null}
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{culture.difficulty}</Text>
          </View>
        </View>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {culture.phase === 'idle' ? (
        <View style={styles.chronoCard}>
          <Text style={styles.chronoTarget}>10 questions de culture générale. Le titre est affiché à l'écran.</Text>
          <Pressable style={styles.primaryButton} onPress={onStart}>
            <Text style={styles.primaryButtonText}>▶︎ Commencer</Text>
          </Pressable>
        </View>
      ) : null}

      {culture.phase === 'selecting' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Question {culture.current_index}/{total}</Text>
          <Text style={styles.helperText}>Choisis la difficulté de la question.</Text>
          <View style={styles.gamePickerRow}>
            {DIFFICULTY_CHOICES.map((option) => (
              <Pressable key={option.key} style={styles.difficultyChip} onPress={() => onSelectDifficulty(option.key)}>
                <Text style={styles.gameChipText}>{option.label}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}

      {culture.phase === 'question' && question ? (
        <>
          <View style={styles.liveCard}>
            <Text style={styles.nowPlayingLabel}>Question (visible à l'écran)</Text>
            <Text style={styles.questionText}>{question.question}</Text>
            <View style={styles.answerCard}>
              <Text style={styles.nowPlayingLabel}>Réponse (régie uniquement)</Text>
              <Text style={styles.answerText}>{question.answer}</Text>
              <Text style={styles.helperText}>{question.explanation}</Text>
            </View>
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Buzzers</Text>
            <Text style={styles.helperText}>Buzzer actif : {culture.current_buzzer_team ?? '—'}</Text>
            <View style={styles.scoreGrid}>
              {teams.map((team, index) => {
                const active = culture.current_buzzer_team === team;
                return (
                  <Pressable
                    key={team}
                    style={[styles.scoreTile, active && styles.scoreTileActive]}
                    onPress={() => onBuzz(team)}
                  >
                    <Text style={styles.scoreTileLabel}>{team}</Text>
                    <Text style={styles.scoreTileValue}>{culture.scores?.[team] ?? 0}</Text>
                    <Text style={styles.scoreTileHint}>Touche {buzzerKeys[index] ?? index + 1}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Validation présentateur</Text>
            <View style={styles.actionRowWrap}>
              <Pressable
                style={[styles.primaryButtonCompact, styles.successButton, !answerPending && styles.primaryButtonDisabled]}
                onPress={() => onAnswer(true)}
                disabled={!answerPending}
              >
                <Text style={styles.primaryButtonText}>Vrai (+1)</Text>
              </Pressable>
              <Pressable
                style={[styles.primaryButtonCompact, styles.falseButton, !answerPending && styles.primaryButtonDisabled]}
                onPress={() => onAnswer(false)}
                disabled={!answerPending}
              >
                <Text style={styles.primaryButtonText}>Faux</Text>
              </Pressable>
              <Pressable
                style={[styles.primaryButtonCompact, !canGoNext && styles.primaryButtonDisabled]}
                onPress={onNext}
                disabled={!canGoNext}
              >
                <Text style={styles.primaryButtonText}>Question suivante</Text>
              </Pressable>
            </View>
            <Text style={styles.helperText}>
              {volumeButtonsActive
                ? '🔊 Volume haut = Vrai puis Suivant après validation · 🔉 Volume bas = Faux'
                : 'Boutons volume inactifs (uniquement en APK).'}
            </Text>
          </View>
        </>
      ) : null}
    </>
  );
}
