import { useEffect } from 'react';
import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStart: () => void;
  onBuzz: (team: string) => void;
  onBeginAfterRoll: () => void;
  onPreviousTeam: () => void;
  onBack: () => void;
};

const dieInstruction = (result: string, sound: string): string => {
  if (result === 'TIC') return `Le mot doit commencer par « ${sound} ».`;
  if (result === 'TAC') return `Le mot doit finir par « ${sound} ».`;
  return `Le mot doit commencer ou finir par « ${sound} ».`;
};

export function BombeLiveScreen({
  snapshot,
  errorMessage,
  onStart,
  onBuzz,
  onBeginAfterRoll,
  onPreviousTeam,
  onBack,
}: Props) {
  const bombe = snapshot.session.bombe;
  const teams = snapshot.settings.teams;
  const currentTeam = teams[bombe.current_team_index] ?? '—';
  const canGoBack = bombe.phase === 'running' && bombe.turn_history.length >= 2;
  const eligibleTeams = new Set(bombe.eligible_team_indices);
  const isTiebreakPending = bombe.phase === 'exploded' && !bombe.winner_team;
  const rollerTeam = bombe.roller_team_index === null ? '—' : teams[bombe.roller_team_index] ?? '—';

  useEffect(() => {
    if (bombe.phase !== 'rolling' || bombe.die_reveal_at_ms <= 0) return;
    let retryTimer: ReturnType<typeof setInterval> | undefined;
    const timer = setTimeout(() => {
      onBeginAfterRoll();
      retryTimer = setInterval(onBeginAfterRoll, 1_000);
    }, Math.max(bombe.die_reveal_at_ms - Date.now(), 0));
    return () => {
      clearTimeout(timer);
      if (retryTimer) clearInterval(retryTimer);
    };
  }, [bombe.die_reveal_at_ms, bombe.phase, onBeginAfterRoll]);

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>La Bombe</Text>
        <Text style={styles.title}>{snapshot.settings.game_title}</Text>
        <Text style={styles.subtitle}>Le BOUM ajoute 1 pénalité. Le plus petit score remporte la manche.</Text>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {bombe.phase === 'idle' ? (
        <View style={styles.bombeCard}>
          <Text style={styles.bombeInstruction}>Prépare le son et désigne l’équipe qui lancera le dé.</Text>
          <Pressable style={styles.primaryButton} onPress={onStart}>
            <Text style={styles.primaryButtonText}>🎲 Préparer la manche</Text>
          </Pressable>
        </View>
      ) : null}

      {bombe.phase === 'awaiting_roll' ? (
        <View style={styles.bombeCard}>
          <Text style={styles.nowPlayingLabel}>Son imposé</Text>
          <Text style={styles.bombeLetter}>{bombe.sound}</Text>
          <Text style={styles.bombeTeam}>{rollerTeam} doit lancer le dé</Text>
          <Text style={styles.bombeInstruction}>Utilise le buzzer de cette équipe pour choisir TIC, TAC ou BOUM.</Text>
          <Pressable style={styles.primaryButton} onPress={() => onBuzz(rollerTeam)}>
            <Text style={styles.primaryButtonText}>🎲 Tester le buzzer de {rollerTeam}</Text>
          </Pressable>
        </View>
      ) : null}

      {bombe.phase === 'rolling' ? (
        <View style={styles.bombeCard}>
          <Text style={styles.bombeLetter}>🎲</Text>
          <Text style={styles.bombeTeam}>Le dé tourne…</Text>
          <Text style={styles.bombeInstruction}>Son de la manche : {bombe.sound}</Text>
        </View>
      ) : null}

      {bombe.phase === 'running' ? (
        <>
          <View style={styles.bombeCard}>
            {bombe.tiebreak_round > 0 ? <Text style={styles.eyebrow}>Départage {bombe.tiebreak_round}</Text> : null}
            <Text style={styles.bombeTeam}>🎲 {bombe.die_result}</Text>
            <Text style={styles.bombeInstruction}>{dieInstruction(bombe.die_result, bombe.sound)}</Text>
            <Text style={styles.nowPlayingLabel}>Son imposé</Text>
            <Text style={styles.bombeLetter}>{bombe.sound}</Text>
            <Text style={styles.nowPlayingLabel}>À toi de jouer</Text>
            <Text style={styles.bombeTeam}>{currentTeam}</Text>
            <Text style={styles.bombeInstruction}>Respecte la règle du dé, puis buzze pour passer la bombe.</Text>
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>Passer la bombe</Text>
            <View style={styles.scoreGrid}>
              {teams.map((team, index) => {
                const isCurrent = index === bombe.current_team_index;
                const isEligible = eligibleTeams.has(index);
                return (
                  <Pressable
                    key={team}
                    style={[styles.scoreTile, isCurrent && styles.scoreTileActive, !isCurrent && styles.primaryButtonDisabled]}
                    onPress={() => onBuzz(team)}
                    disabled={!isCurrent}
                  >
                    <Text style={styles.scoreTileLabel}>{team}</Text>
                    <Text style={styles.scoreTileValue}>{bombe.scores[team] ?? 0}</Text>
                    <Text style={styles.scoreTileHint}>
                      {isCurrent ? 'Buzzer maintenant' : isEligible ? 'En attente' : 'Hors course'}
                    </Text>
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
          <View style={styles.scoreGrid}>
            {teams.map((team) => (
              <View key={team} style={styles.scoreTile}>
                <Text style={styles.scoreTileLabel}>{team}</Text>
                <Text style={styles.scoreTileValue}>{bombe.scores[team] ?? 0}</Text>
                <Text style={styles.scoreTileHint}>point{(bombe.scores[team] ?? 0) > 1 ? 's' : ''} de pénalité</Text>
              </View>
            ))}
          </View>
          {bombe.winner_team ? (
            <Text style={styles.bombeTeam}>🏆 {bombe.winner_team} remporte la manche</Text>
          ) : null}
          {isTiebreakPending ? (
            <>
              <Text style={styles.bombeInstruction}>Égalité au plus petit score : une partie décisive est nécessaire.</Text>
              <Pressable style={styles.primaryButton} onPress={onStart}>
                <Text style={styles.primaryButtonText}>💣 Commencer le départage</Text>
              </Pressable>
            </>
          ) : null}
        </View>
      ) : null}
    </>
  );
}
