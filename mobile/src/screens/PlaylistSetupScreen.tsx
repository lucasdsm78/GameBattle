import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot | null;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  onReloadPlaylist: () => void;
  onContinue: () => void;
  onBack: () => void;
};

const BLINDTEST_TRACKS_PER_ROUND = 10;

export function PlaylistSetupScreen({
  snapshot,
  connectionState,
  errorMessage,
  onReloadPlaylist,
  onContinue,
  onBack,
}: Props) {
  const activeGameKey = snapshot?.session.active_round?.game_key;
  const blindtest = snapshot?.session.blindtest;
  const loadedCount = blindtest?.tracks.length ?? 0;
  const isBlindtestRound = activeGameKey === 'blindtest';
  const playlistReady = Boolean(activeGameKey) && (!isBlindtestRound || loadedCount >= BLINDTEST_TRACKS_PER_ROUND);

  return (
    <>
      <View style={styles.stepper}>
        <View style={[styles.stepPill, styles.stepPillDone]}>
          <Text style={styles.stepPillText}>1 · Config</Text>
        </View>
        <View style={[styles.stepPill, styles.stepPillActive]}>
          <Text style={[styles.stepPillText, styles.stepPillTextActive]}>2 · Playlist</Text>
        </View>
        <View style={styles.stepPill}>
          <Text style={styles.stepPillText}>3 · Live</Text>
        </View>
      </View>

      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Modifier la configuration</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Préparation</Text>
        <Text style={styles.title}>Playlist fixe</Text>
        <Text style={styles.subtitle}>
          GameBattle utilise toujours la playlist configurée côté serveur. Une manche blindtest jouera exactement 10 musiques,
          peu importe la taille de la playlist Spotify source.
        </Text>
        <View style={styles.badgeRow}>
          <View style={[styles.badge, connectionState === 'connected' ? styles.badgeSuccess : styles.badgeWarning]}>
            <Text style={styles.badgeText}>{connectionState}</Text>
          </View>
          <View style={[styles.badge, playlistReady ? styles.badgeSuccess : styles.badgeWarning]}>
            <Text style={styles.badgeText}>{playlistReady ? 'prête' : 'à charger'}</Text>
          </View>
        </View>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>État de la manche</Text>
        {snapshot ? (
          <>
            <View style={styles.importedCard}>
              <Text style={styles.inputLabel}>Jeu tiré</Text>
              <Text style={styles.importedName}>{snapshot.session.active_round?.label ?? 'En attente'} · {activeGameKey ?? '—'}</Text>
            </View>

            {isBlindtestRound ? (
              <>
                <View style={styles.importedCard}>
                  <Text style={styles.inputLabel}>Playlist</Text>
                  <Text style={styles.importedName}>{blindtest?.playlist_name || 'Playlist serveur non chargée'}</Text>
                  <Text style={styles.helperText}>
                    {loadedCount}/{BLINDTEST_TRACKS_PER_ROUND} musiques prêtes pour cette manche.
                  </Text>
                </View>
                <Pressable style={styles.secondaryButton} onPress={onReloadPlaylist} disabled={connectionState !== 'connected'}>
                  <Text style={styles.secondaryButtonText}>Recharger la playlist fixe</Text>
                </Pressable>
              </>
            ) : (
              <Text style={styles.helperText}>
                La première manche tirée n’est pas un blindtest. Tu peux passer directement au live.
              </Text>
            )}
          </>
        ) : (
          <Text style={styles.helperText}>Synchronisation avec le backend…</Text>
        )}
      </View>

      <Pressable
        style={[styles.primaryButton, (!playlistReady || !snapshot) && styles.primaryButtonDisabled]}
        onPress={onContinue}
        disabled={!playlistReady || !snapshot}
      >
        <Text style={styles.primaryButtonText}>Valider la playlist et lancer le live</Text>
      </Pressable>
    </>
  );
}
