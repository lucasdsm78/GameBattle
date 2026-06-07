import { useMemo } from 'react';
import { Pressable, Switch, Text, View } from 'react-native';
import { Field } from '../components/Field';
import { colors, styles } from '../theme';
import { GameDraft } from '../types/gameConfig';

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

const rebuildRounds = (draft: GameDraft, roundCount: number): GameDraft['rounds'] =>
  Array.from({ length: roundCount }, (_, index) => ({
    id: `blindtest-round-${index + 1}`,
    label: draft.settings.random_round_order ? `Blindtest aléatoire ${index + 1}` : `Blindtest ${index + 1}`,
    game_key: 'blindtest' as const,
    planned_track_count: 10,
    buzzer_enabled: true,
  }));

export function ConfigScreen({ draft, setDraft, connectionState, errorMessage, onValidate }: Props) {
  const teams = draft.settings.teams;
  const buzzerKeys = draft.settings.buzzer_keys;

  const canValidate = useMemo(() => {
    const titleOk = draft.settings.game_title.trim().length >= 3;
    const teamsOk = teams.length >= 2 && teams.every((team) => team.trim().length >= 2);
    return titleOk && teamsOk && connectionState === 'connected';
  }, [draft.settings.game_title, teams, connectionState]);

  const updateTitle = (value: string) => {
    const next = cloneDraft(draft);
    next.settings.game_title = value;
    setDraft(next);
  };

  const updateRandomOrder = (value: boolean) => {
    const next = cloneDraft(draft);
    next.settings.random_round_order = value;
    next.rounds = rebuildRounds(next, next.rounds.length);
    setDraft(next);
  };

  const updateRoundCount = (value: string) => {
    const roundCount = Math.min(Math.max(Number.parseInt(value || '1', 10) || 1, 1), 12);
    const next = cloneDraft(draft);
    next.games[0].round_count = roundCount;
    next.rounds = rebuildRounds(next, roundCount);
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
        <Text style={styles.subtitle}>Règle le titre, le mode et les équipes, puis valide pour choisir la playlist.</Text>
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
          <Text style={styles.inputLabel}>Manches aléatoires</Text>
          <Switch
            value={draft.settings.random_round_order}
            onValueChange={updateRandomOrder}
            trackColor={{ false: '#4b5563', true: colors.accentDark }}
            thumbColor={colors.text}
          />
        </View>

        <Field
          label="Nombre de manches blindtest"
          keyboardType="number-pad"
          value={String(draft.games[0]?.round_count ?? 1)}
          onChangeText={updateRoundCount}
        />
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
          <Text style={styles.summaryValue}>{draft.rounds.length}</Text>
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
