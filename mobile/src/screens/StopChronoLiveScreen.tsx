import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onStop: () => void;
  onNext: () => void;
  onBack: () => void;
};

const seconds = (ms: number): string => `${(ms / 1000).toFixed(3).replace('.', ',')} s`;

export function StopChronoLiveScreen({ snapshot, errorMessage, onStart, onStop, onNext, onBack }: Props) {
  const chrono = snapshot.session.stopchrono;
  const teams = snapshot.settings.teams;
  const currentTeam = chrono.current_team;
  // Avec la rotation, la position dans le tour vient du nombre d'équipes qui ont déjà joué.
  const playedCount = Object.keys(chrono.results).length;
  const teamPosition = Math.min(chrono.phase === 'revealed' ? playedCount : playedCount + 1, teams.length);
  const roundComplete = playedCount >= teams.length;
  const lastRound = chrono.round_number >= chrono.rounds_total;

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer la partie</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Stop Chrono en direct</Text>
        <Text style={styles.title}>{snapshot.settings.game_title}</Text>
        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>Tour {chrono.round_number}/{chrono.rounds_total}</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>Cible {chrono.target_seconds}s</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>Équipe {teamPosition}/{teams.length}</Text>
          </View>
          <View style={[styles.badge, chrono.phase === 'running' ? styles.badgeSuccess : styles.badgeWarning]}>
            <Text style={styles.badgeText}>{chrono.phase}</Text>
          </View>
        </View>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {chrono.phase !== 'finished' ? (
        <View style={styles.chronoCard}>
          <Text style={styles.nowPlayingLabel}>Au tour de</Text>
          <Text style={styles.nowPlayingTitle}>{currentTeam ?? '—'}</Text>
          <Text style={styles.chronoTarget}>Arrête-toi le plus près de {chrono.target_seconds}s</Text>

          {chrono.phase === 'idle' ? (
            <Pressable style={styles.primaryButton} onPress={onStart}>
              <Text style={styles.primaryButtonText}>▶︎ Démarrer le chrono</Text>
            </Pressable>
          ) : null}

          {chrono.phase === 'running' ? (
            <Pressable style={[styles.primaryButton, styles.falseButton]} onPress={onStop}>
              <Text style={styles.primaryButtonText}>⏹ STOP</Text>
            </Pressable>
          ) : null}

          {chrono.phase === 'revealed' && currentTeam ? (
            <View style={styles.chronoResult}>
              <Text style={styles.chronoResultTime}>{seconds(chrono.results[currentTeam] ?? 0)}</Text>
              <Text style={styles.chronoResultDelta}>écart {seconds(chrono.deltas_ms[currentTeam] ?? 0)}</Text>
              <Pressable style={styles.primaryButton} onPress={onNext}>
                <Text style={styles.primaryButtonText}>
                  {!roundComplete ? 'Équipe suivante' : lastRound ? 'Voir le résultat' : `Tour ${chrono.round_number + 1} →`}
                </Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : null}

      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Erreur totale</Text>
        <Text style={styles.helperText}>Les écarts des 3 tours s’additionnent : la plus petite erreur gagne.</Text>
        <View style={styles.scoreGrid}>
          {teams.map((team) => {
            const played = team in chrono.results;
            const active = team === currentTeam && chrono.phase !== 'finished';
            return (
              <View key={team} style={[styles.scoreTile, active && styles.scoreTileActive]}>
                <Text style={styles.scoreTileLabel}>{team}</Text>
                <Text style={styles.scoreTileValue}>{seconds(chrono.total_errors_ms[team] ?? 0)}</Text>
                <Text style={styles.scoreTileHint}>
                  {played ? `ce tour : écart ${seconds(chrono.deltas_ms[team] ?? 0)}` : 'pas encore joué ce tour'}
                  {chrono.scores[team] ? ` · +${chrono.scores[team]}` : ''}
                </Text>
              </View>
            );
          })}
        </View>
        {chrono.winner_team ? (
          <Text style={styles.winnerText}>🏆 Vainqueur de la manche : {chrono.winner_team}</Text>
        ) : null}
      </View>
    </>
  );
}