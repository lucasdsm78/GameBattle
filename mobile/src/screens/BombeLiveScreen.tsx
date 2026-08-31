import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onBuzz: (team: string) => void;
  onPreviousTeam: () => void;
  onBack: () => void;
};

export function BombeLiveScreen({ snapshot, errorMessage, onStart, onBuzz, onPreviousTeam, onBack }: Props) {
  const bombe = snapshot.session.bombe;
  const teams = snapshot.settings.teams;
  const currentTeam = teams[bombe.current_team_index] ?? '—';
  const canGoBack = bombe.phase === 'running' && bombe.turn_history.length >= 2;

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>La Bombe</Text>
        <Text style={styles.title}>{snapshot.settings.game_title}</Text>
        <Text style={styles.subtitle}>Trouve un mot avec la lettre, puis buzze pour passer la bombe.</Text>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {bombe.phase === 'idle' ? (
        <View style={styles.bombeCard}>
          <Text style={styles.bombeInstruction}>La durée est choisie secrètement et aléatoirement.</Text>
          <Pressable style={styles.primaryButton} onPress={onStart}>
            <Text style={styles.primaryButtonText}>💣 Commencer</Text>
          </Pressable>
        </View>
      ) : null}

      {bombe.phase === 'running' ? (
        <>
          <View style={styles.bombeCard}>
            <Text style={styles.nowPlayingLabel}>Lettre imposée</Text>
            <Text style={styles.bombeLetter}>{bombe.letter}</Text>
            <Text style={styles.nowPlayingLabel}>À toi de jouer</Text>
            <Text style={styles.bombeTeam}>{currentTeam}</Text>
            <Text style={styles.bombeInstruction}>Dis un mot contenant la lettre « {bombe.letter} », puis buzze.</Text>
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Passer la bombe</Text>
            <View style={styles.scoreGrid}>
              {teams.map((team, index) => {
                const isCurrent = index === bombe.current_team_index;
                return (
                  <Pressable
                    key={team}
                    style={[styles.scoreTile, isCurrent && styles.scoreTileActive, !isCurrent && styles.primaryButtonDisabled]}
                    onPress={() => onBuzz(team)}
                    disabled={!isCurrent}
                  >
                    <Text style={styles.scoreTileLabel}>{team}</Text>
                    <Text style={styles.scoreTileHint}>{isCurrent ? 'Buzzer maintenant' : 'En attente'}</Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Arbitrage</Text>
            <Text style={styles.helperText}>Mot incorrect ? Rends immédiatement la bombe à l’équipe précédente.</Text>
            <Pressable
              style={[styles.falseButton, styles.primaryButton, !canGoBack && styles.primaryButtonDisabled]}
              onPress={onPreviousTeam}
              disabled={!canGoBack}
            >
              <Text style={styles.primaryButtonText}>↩ Revenir à l’équipe précédente</Text>
            </Pressable>
          </View>
        </>
      ) : null}

      {bombe.phase === 'exploded' ? (
        <View style={styles.bombeCard}>
          <Text style={styles.bombeLetter}>BOUM</Text>
          <Text style={styles.bombeInstruction}>La bombe a explosé chez {bombe.exploded_team}.</Text>
          <Text style={styles.bombeTeam}>🏆 {bombe.winner_team}</Text>
        </View>
      ) : null}
    </>
  );
}
