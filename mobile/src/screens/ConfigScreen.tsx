import { useMemo } from 'react';
import { Pressable, Switch, Text, View } from 'react-native';
import { Field } from '../components/Field';
import { colors, styles } from '../theme';
import { CultureDifficulty, GameDraft, GameKey } from '../types/gameConfig';

const GAME_LABELS: Record<GameKey, string> = { blindtest: 'Blindtest', stopchrono: 'Stop Chrono', culture: 'Culture générale' };
const GAME_KEYS: GameKey[] = ['blindtest', 'stopchrono', 'culture'];
const CULTURE_DIFFICULTIES: { key: CultureDifficulty; label: string }[] = [
  { key: 'toutes', label: 'Toutes' },
  { key: 'facile', label: 'Facile' },
  { key: 'moyen', label: 'Moyen' },
  { key: 'difficile', label: 'Difficile' },
];

type Props = {
  draft: GameDraft;
  setDraft: (draft: GameDraft) => void;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  onValidate: () => void;
};

const defaultBuzzerKey = (index: number) => `${index + 1}`;

const cloneDraft = (draft: GameDraft): GameDraft => ({
  settings: {
    ...draft.settings,
    teams: [...draft.settings.teams],
    buzzer_keys: [...draft.settings.buzzer_keys],
  },
  games: draft.games.map((game) => ({ ...game })),
  rounds: draft.rounds.map((round) => ({ ...round })),
  status: draft.status,
});

const ensureGame = (draft: GameDraft, key: GameKey) =>
  draft.games.find((game) => game.game_key === key) ?? { game_key: key, label: GAME_LABELS[key], enabled: false, round_count: 0 };

export function ConfigScreen({ draft, setDraft, connectionState, errorMessage, onValidate }: Props) {
  const teams = draft.settings.teams;
  const buzzerKeys = draft.settings.buzzer_keys;
  const enabledCount = draft.games.filter((game) => game.enabled).length;

  const canValidate = useMemo(() => {
    const titleOk = draft.settings.game_title.trim().length >= 3;
    const teamsOk = teams.length >= 2 && teams.every((team) => team.trim().length >= 2);
    const gamesOk = draft.games.some((game) => game.enabled);
    return titleOk && teamsOk && gamesOk && connectionState === 'connected';
  }, [draft.settings.game_title, teams, draft.games, connectionState]);

  const updateTitle = (value: string) => {
    const next = cloneDraft(draft);
    next.settings.game_title = value;
    setDraft(next);
  };

  const isGameEnabled = (key: GameKey) => draft.games.some((game) => game.game_key === key && game.enabled);

  const toggleGame = (key: GameKey) => {
    const enabled = isGameEnabled(key);
    // On garde toujours au moins un jeu sélectionné.
    if (enabled && enabledCount <= 1) {
      return;
    }
    const next = cloneDraft(draft);
    next.games = GAME_KEYS.map((gameKey) => {
      const existing = ensureGame(next, gameKey);
      return { ...existing, label: GAME_LABELS[gameKey], enabled: gameKey === key ? !enabled : existing.enabled };
    });
    setDraft(next);
  };

  const updateRandomOrder = (value: boolean) => {
    const next = cloneDraft(draft);
    next.settings.random_round_order = value;
    setDraft(next);
  };

  const updateTotalRounds = (value: string) => {
    const total = Math.min(Math.max(Number.parseInt(value || '1', 10) || 1, 1), 30);
    const next = cloneDraft(draft);
    next.settings.total_rounds = total;
    setDraft(next);
  };

  const updateCultureDifficulty = (difficulty: CultureDifficulty) => {
    const next = cloneDraft(draft);
    next.settings.culture_difficulty = difficulty;
    setDraft(next);
  };

  const updateTeam = (index: number, value: string) => {
    const next = cloneDraft(draft);
    next.settings.teams[index] = value;
    setDraft(next);
  };

  const updateBuzzerKey = (index: number, value: string) => {
    const next = cloneDraft(draft);
    next.settings.buzzer_keys[index] = value;
    setDraft(next);
  };

  const addTeam = () => {
    if (teams.length >= 6) {
      return;
    }
    const next = cloneDraft(draft);
    next.settings.teams.push(`Équipe ${next.settings.teams.length + 1}`);
    next.settings.buzzer_keys.push(defaultBuzzerKey(next.settings.buzzer_keys.length));
    setDraft(next);
  };

  const removeTeam = (index: number) => {
    if (teams.length <= 2) {
      return;
    }
    const next = cloneDraft(draft);
    next.settings.teams.splice(index, 1);
    next.settings.buzzer_keys.splice(index, 1);
    setDraft(next);
  };

  return (
    <>
      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>GameBattle Controller</Text>
        <Text style={styles.title}>Configuration de la partie</Text>
        <Text style={styles.subtitle}>Choisis le jeu, règle le mode et les équipes, puis valide pour lancer la partie.</Text>
        <View style={styles.badgeRow}>
          <View style={[styles.badge, connectionState === 'connected' ? styles.badgeSuccess : styles.badgeWarning]}>
            <Text style={styles.badgeText}>{connectionState}</Text>
          </View>
        </View>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Partie</Text>
        <Field label="Titre de la partie" value={draft.settings.game_title} onChangeText={updateTitle} />

        <View style={styles.switchRow}>
          <Text style={styles.inputLabel}>Jeux aléatoires</Text>
          <Switch
            value={draft.settings.random_round_order}
            onValueChange={updateRandomOrder}
            trackColor={{ false: '#4b5563', true: colors.accentDark }}
            thumbColor={colors.text}
          />
        </View>

        <Text style={styles.inputLabel}>Jeux de la partie</Text>
        <View style={styles.gamePickerRow}>
          {GAME_KEYS.map((key) => {
            const active = isGameEnabled(key);
            return (
              <Pressable
                key={key}
                style={[styles.gameChip, active && styles.gameChipActive]}
                onPress={() => toggleGame(key)}
              >
                <Text style={[styles.gameChipText, active && styles.gameChipTextActive]}>{GAME_LABELS[key]}</Text>
              </Pressable>
            );
          })}
        </View>
        <Text style={styles.helperText}>
          {draft.settings.random_round_order
            ? 'Ordre des jeux mélangé et caché — réparti équitablement entre les jeux sélectionnés.'
            : 'Ordre prévisible (round-robin entre les jeux sélectionnés).'}
        </Text>

        <Field
          label="Nombre de manches"
          keyboardType="number-pad"
          value={String(draft.settings.total_rounds)}
          onChangeText={updateTotalRounds}
        />

        {isGameEnabled('culture') ? (
          <>
            <Text style={styles.inputLabel}>Difficulté culture générale (optionnel)</Text>
            <View style={styles.gamePickerRow}>
              {CULTURE_DIFFICULTIES.map((option) => {
                const active = draft.settings.culture_difficulty === option.key;
                return (
                  <Pressable
                    key={option.key}
                    style={[styles.difficultyChip, active && styles.gameChipActive]}
                    onPress={() => updateCultureDifficulty(option.key)}
                  >
                    <Text style={[styles.gameChipText, active && styles.gameChipTextActive]}>{option.label}</Text>
                  </Pressable>
                );
              })}
            </View>
          </>
        ) : null}
      </View>

      <View style={styles.sectionCard}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Équipes</Text>
          <Pressable style={styles.secondaryButton} onPress={addTeam} disabled={teams.length >= 6}>
            <Text style={styles.secondaryButtonText}>Ajouter</Text>
          </Pressable>
        </View>
        <Text style={styles.helperText}>Touche clavier (ou bouton USB) envoyée par équipe pour buzzer depuis l’écran.</Text>

        {teams.map((team, index) => (
          <View key={`team-${index}`} style={styles.teamRow}>
            <Field label={`Équipe ${index + 1}`} value={team} onChangeText={(value) => updateTeam(index, value)} />
            <Field
              label="Touche buzzer"
              value={buzzerKeys[index] ?? ''}
              onChangeText={(value) => updateBuzzerKey(index, value)}
              placeholder={defaultBuzzerKey(index)}
              autoCapitalize="none"
            />
            <Pressable onPress={() => removeTeam(index)} disabled={teams.length <= 2}>
              <Text style={[styles.removeText, teams.length <= 2 && styles.removeTextDisabled]}>Supprimer</Text>
            </Pressable>
          </View>
        ))}
      </View>

      <View style={styles.summaryCard}>
        <View>
          <Text style={styles.summaryLabel}>Équipes</Text>
          <Text style={styles.summaryValue}>{teams.length}</Text>
        </View>
        <View>
          <Text style={styles.summaryLabel}>Manches</Text>
          <Text style={styles.summaryValue}>{draft.settings.total_rounds}</Text>
        </View>
        <View>
          <Text style={styles.summaryLabel}>Mode</Text>
          <Text style={styles.summaryValue}>{draft.settings.random_round_order ? 'Aléa' : 'Manuel'}</Text>
        </View>
      </View>

      <Pressable
        style={[styles.primaryButton, !canValidate && styles.primaryButtonDisabled]}
        onPress={onValidate}
        disabled={!canValidate}
      >
        <Text style={styles.primaryButtonText}>Valider</Text>
      </Pressable>
    </>
  );
}
