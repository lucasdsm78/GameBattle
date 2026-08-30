import { Pressable, Text, View } from 'react-native';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';
import { useVolumeButtons } from '../hooks/useVolumeButtons';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onPlay: () => void;
  onPause: () => void;
  onBuzz: (team: string) => void;
  onAnswer: (isCorrect: boolean) => void;
  onNext: () => void;
  onReloadPlaylist: () => void;
  onBack: () => void;
};

export function LiveScreen({
  snapshot,
  errorMessage,
  onPlay,
  onPause,
  onBuzz,
  onAnswer,
  onNext,
  onReloadPlaylist,
  onBack,
}: Props) {
  const blindtest = snapshot.session.blindtest;
  const teams = snapshot.settings.teams;
  const buzzerKeys = snapshot.settings.buzzer_keys;
  const track = blindtest.current_track;
  const isPlaying = blindtest.playback_state === 'playing';
  const total = Math.max(blindtest.total_tracks, 1);
  // total_tracks reflète le nombre planifié (10) même sans import ; on teste les pistes réellement chargées.
  const hasPlaylist = blindtest.tracks.length > 0;

  // Une équipe a buzzé et attend la validation du présentateur.
  const answerPending = Boolean(blindtest.current_buzzer_team) && !blindtest.revealed;
  const canGoNext = Boolean(blindtest.current_buzzer_team) && blindtest.revealed && !blindtest.winner_team;

  // Boutons volume physiques (actifs uniquement en APK / dev build) :
  //  - Volume haut → Vrai (+1) si une équipe a buzzé ; sinon Suivant si la réponse est révélée ; sinon rien.
  //  - Volume bas  → Faux, uniquement si une équipe a buzzé ; sinon rien.
  const volumeButtonsActive = useVolumeButtons({
    enabled: true,
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
        <Text style={styles.eyebrow}>Blindtest en direct</Text>
        <Text style={styles.title}>{snapshot.settings.game_title}</Text>
        <View style={styles.badgeRow}>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>Musique {blindtest.current_track_index}/{total}</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>Reste {blindtest.tracks_remaining}</Text>
          </View>
          <View style={[styles.badge, isPlaying ? styles.badgeSuccess : styles.badgeWarning]}>
            <Text style={styles.badgeText}>{blindtest.playback_state}</Text>
          </View>
        </View>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {!hasPlaylist ? (
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Playlist non chargée</Text>
          <Text style={styles.helperText}>
            La playlist n’a pas pu être importée automatiquement. Vérifie que Spotify est connecté sur l’écran, puis recharge.
          </Text>
          <Pressable style={styles.secondaryButton} onPress={onReloadPlaylist}>
            <Text style={styles.secondaryButtonText}>Recharger la playlist</Text>
          </Pressable>
        </View>
      ) : null}

      <View style={styles.liveCard}>
        <Text style={styles.nowPlayingLabel}>Réponse (visible régie uniquement)</Text>
        <Text style={styles.nowPlayingTitle}>{track?.title ?? '—'}</Text>
        <Text style={styles.nowPlayingArtist}>{track?.artist ?? 'En attente de lecture'}</Text>
        <Text style={styles.helperText}>Le son sort de l’écran. Le titre reste masqué pour le public jusqu’à la révélation.</Text>
        <View style={styles.actionRowWrap}>
          {isPlaying ? (
            <Pressable style={[styles.primaryButtonCompact, styles.falseButton]} onPress={onPause}>
              <Text style={styles.primaryButtonText}>⏸ Pause</Text>
            </Pressable>
          ) : (
            <Pressable style={styles.primaryButtonCompact} onPress={onPlay}>
              <Text style={styles.primaryButtonText}>▶︎ Lecture</Text>
            </Pressable>
          )}
        </View>
      </View>

      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Buzzers</Text>
        <Text style={styles.helperText}>Buzzer actif : {blindtest.current_buzzer_team ?? '—'}</Text>
        <View style={styles.scoreGrid}>
          {teams.map((team, index) => {
            const active = blindtest.current_buzzer_team === team;
            return (
              <Pressable
                key={team}
                style={[styles.scoreTile, active && styles.scoreTileActive]}
                onPress={() => onBuzz(team)}
              >
                <Text style={styles.scoreTileLabel}>{team}</Text>
                <Text style={styles.scoreTileValue}>{blindtest.scores?.[team] ?? 0}</Text>
                <Text style={styles.scoreTileHint}>Touche {buzzerKeys[index] ?? index + 1} · buzz test</Text>
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
            <Text style={styles.primaryButtonText}>Musique suivante</Text>
          </Pressable>
        </View>
        <Text style={styles.helperText}>
          {volumeButtonsActive
            ? '🔊 Volume haut = Vrai puis Suivant après révélation · 🔉 Volume bas = Faux'
            : 'Boutons volume inactifs (uniquement en APK / dev build). Utilise les boutons ci-dessus.'}
        </Text>
        {blindtest.winner_team ? (
          <Text style={styles.winnerText}>🏆 Gagnant de la manche : {blindtest.winner_team}</Text>
        ) : null}
      </View>
    </>
  );
}
