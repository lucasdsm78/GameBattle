import { useEffect, useMemo, useState } from 'react';
import {
  Linking,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from 'react-native';
import { StatusBar as ExpoStatusBar } from 'expo-status-bar';
import { useBlindtestAudioProviders } from './src/hooks/useBlindtestAudioProviders';
import {
  getBlindtestAudioModeLabel,
  openSpotifyTrack,
  resolveBlindtestAudioMode,
} from './src/services/audio/spotifyPlayback';
import { GameConfigControllerSocket } from './src/services/realtime/gameConfigControllerSocket';
import { useGameConfigStore } from './src/store/gameConfigStore';
import { BlindtestPlaylistSeedTrack, GameDraft } from './src/types/gameConfig';

const socket = new GameConfigControllerSocket();

const defaultPlaylist: BlindtestPlaylistSeedTrack[] = [
  {
    title: 'Blinding Lights',
    artist: 'The Weeknd',
    preview_url: 'https://example.com/audio1.mp3',
    artwork_url: 'https://example.com/art1.jpg',
  },
  {
    title: 'One More Time',
    artist: 'Daft Punk',
    preview_url: 'https://example.com/audio2.mp3',
    artwork_url: 'https://example.com/art2.jpg',
  },
  {
    title: 'Titanium',
    artist: 'David Guetta & Sia',
    preview_url: 'https://example.com/audio3.mp3',
    artwork_url: 'https://example.com/art3.jpg',
  },
];

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

export default function App() {
  const {
    draft,
    remoteSnapshot,
    connectionState,
    errorMessage,
    setDraft,
    setRemoteSnapshot,
    setConnectionState,
    setErrorMessage,
  } = useGameConfigStore();
  const [playlistTracks, setPlaylistTracks] = useState<BlindtestPlaylistSeedTrack[]>(defaultPlaylist);
  const [spotifyPlaylistUrl, setSpotifyPlaylistUrl] = useState('');

  useEffect(() => {
    socket.connect({
      onSnapshot: setRemoteSnapshot,
      onStatusChange: setConnectionState,
      onError: setErrorMessage,
    });

    return () => socket.disconnect();
  }, [setConnectionState, setErrorMessage, setRemoteSnapshot]);

  useEffect(() => {
    if (!remoteSnapshot) {
      return;
    }

    if (remoteSnapshot.session.blindtest.tracks.length > 0) {
      setPlaylistTracks(
        remoteSnapshot.session.blindtest.tracks.map((track) => ({
          title: track.title,
          artist: track.artist,
          preview_url: track.preview_url,
          artwork_url: track.artwork_url,
        })),
      );
    }

    if (remoteSnapshot.session.blindtest.playlist_provider === 'spotify' && remoteSnapshot.session.blindtest.playlist_source_url) {
      setSpotifyPlaylistUrl(remoteSnapshot.session.blindtest.playlist_source_url);
    }
  }, [remoteSnapshot]);

  const blindtestRound = draft.rounds[0];
  const blindtestState = remoteSnapshot?.session.blindtest;
  const teams = draft.settings.teams;
  const buzzerKeys = draft.settings.buzzer_keys;
  const activeTrack = blindtestState?.current_track ?? null;
  const { activeProvider, previewProvider, spotifySdkProvider, spotifyWebApiProvider } = useBlindtestAudioProviders({
    blindtest: blindtestState,
    onSyncPlayback: (payload) => socket.syncPlayback(payload),
    onError: setErrorMessage,
  });
  const spotifyConnected = spotifySdkProvider.canControlPlayback || spotifyWebApiProvider.canControlPlayback;
  const audioMode = resolveBlindtestAudioMode(activeTrack, { spotifyConnected });
  const audioPlayer = previewProvider;
  const spotifyPlayer = activeProvider;
  const canControlPreview = audioMode === 'preview-native' && previewProvider.hasPreview;
  const canControlSpotifyFull = audioMode === 'spotify-full' && activeProvider.canControlPlayback && Boolean(activeTrack?.track_id);
  const canControlPlaybackActions = canControlPreview || canControlSpotifyFull;

  const summary = useMemo(
    () => ({
      teamsCount: draft.settings.teams.length,
      roundCount: draft.rounds.length,
      playlistCount: playlistTracks.length,
    }),
    [draft.rounds.length, draft.settings.teams.length, playlistTracks.length],
  );

  const updateTitle = (value: string) => {
    const next = cloneDraft(draft);
    next.settings.game_title = value;
    setDraft(next);
  };

  const updateRandomOrder = (value: boolean) => {
    const next = cloneDraft(draft);
    next.settings.random_round_order = value;
    setDraft(next);
  };

  const updateTeam = (index: number, value: string) => {
    const next = cloneDraft(draft);
    next.settings.teams[index] = value;
    setDraft(next);
  };

  const addTeam = () => {
    if (draft.settings.teams.length >= 6) {
      return;
    }
    const next = cloneDraft(draft);
    next.settings.teams.push(`Équipe ${next.settings.teams.length + 1}`);
    next.settings.buzzer_keys.push(defaultBuzzerKey(next.settings.buzzer_keys.length));
    setDraft(next);
  };

  const removeTeam = (index: number) => {
    if (draft.settings.teams.length <= 2) {
      return;
    }
    const next = cloneDraft(draft);
    next.settings.teams.splice(index, 1);
    next.settings.buzzer_keys.splice(index, 1);
    setDraft(next);
  };

  const updateBuzzerKey = (index: number, value: string) => {
    const next = cloneDraft(draft);
    next.settings.buzzer_keys[index] = value;
    setDraft(next);
  };

  const updateRoundCount = (value: string) => {
    const roundCount = Math.min(Math.max(Number.parseInt(value || '1', 10) || 1, 1), 12);
    const next = cloneDraft(draft);
    next.games[0].round_count = roundCount;
    next.rounds = Array.from({ length: roundCount }, (_, index) => ({
      id: `blindtest-round-${index + 1}`,
      label: next.settings.random_round_order ? `Blindtest aléatoire ${index + 1}` : `Blindtest ${index + 1}`,
      game_key: 'blindtest',
      planned_track_count: 10,
      buzzer_enabled: true,
    }));
    setDraft(next);
  };

  const updateBuzzerEnabled = (value: boolean) => {
    const next = cloneDraft(draft);
    next.rounds = next.rounds.map((round) => ({ ...round, buzzer_enabled: value }));
    setDraft(next);
  };

  const updatePlaylistTrack = (index: number, field: keyof BlindtestPlaylistSeedTrack, value: string) => {
    setPlaylistTracks((current) => current.map((track, trackIndex) => (trackIndex === index ? { ...track, [field]: value } : track)));
  };

  const addPlaylistTrack = () => {
    setPlaylistTracks((current) => [
      ...current,
      {
        title: `Titre ${current.length + 1}`,
        artist: `Artiste ${current.length + 1}`,
        preview_url: `https://example.com/audio${current.length + 1}.mp3`,
        artwork_url: `https://example.com/art${current.length + 1}.jpg`,
      },
    ]);
  };

  const validateGame = () => {
    socket.replaceConfig({ ...draft, status: 'ready' });
  };

  const launchGame = () => {
    socket.launchGame();
  };

  const loadPlaylist = () => {
    socket.loadBlindtestPlaylist(playlistTracks);
  };

  const importSpotifyPlaylist = () => {
    socket.importSpotifyPlaylist(spotifyPlaylistUrl.trim());
  };

  const markAnswer = (isCorrect: boolean) => {
    socket.answer(isCorrect);
  };

  const controlPlayback = (action: 'play' | 'pause' | 'resume' | 'stop' | 'seek', positionMs?: number) => {
    socket.controlPlayback(action, positionMs);
  };

  const playCurrentTrack = async () => {
    controlPlayback('play');
    if (canControlSpotifyFull && activeTrack) {
      await spotifyPlayer.controls.playTrack(activeTrack, blindtestState?.playback_position_ms ?? 0);
    }
  };

  const pauseCurrentTrack = async () => {
    controlPlayback('pause', previewProvider.positionMs);
    if (canControlSpotifyFull) {
      await spotifyPlayer.controls.pause();
    }
  };

  const resumeCurrentTrack = async () => {
    controlPlayback('resume', previewProvider.positionMs);
    if (canControlSpotifyFull) {
      await spotifyPlayer.controls.resume();
    }
  };

  const stopCurrentTrack = async () => {
    controlPlayback('stop');
    if (canControlSpotifyFull) {
      await spotifyPlayer.controls.stop();
    }
  };

  const nextTrack = () => {
    socket.nextTrack();
  };

  const formatDuration = (milliseconds: number) => {
    const totalSeconds = Math.max(Math.floor(milliseconds / 1000), 0);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, '0')}`;
  };

  const openExternalUrl = async (url: string) => {
    if (!url) {
      return;
    }

    try {
      await Linking.openURL(url);
    } catch {
      setErrorMessage("Impossible d'ouvrir le lien demandé.");
    }
  };

  const openSpotifyTrackInApp = async () => {
    try {
      await openSpotifyTrack(activeTrack);
    } catch {
      setErrorMessage("Impossible d'ouvrir la piste dans Spotify.");
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ExpoStatusBar style="light" />
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.heroCard}>
          <Text style={styles.eyebrow}>GameBattle Controller</Text>
          <Text style={styles.title}>Blindtest • Régie mobile</Text>
          <Text style={styles.subtitle}>
            Configure les manches, valide la partie puis pilote le blindtest en temps réel depuis le mobile.
          </Text>
          <View style={styles.badgeRow}>
            <View style={[styles.badge, connectionState === 'connected' ? styles.badgeSuccess : styles.badgeWarning]}>
              <Text style={styles.badgeText}>{connectionState}</Text>
            </View>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{remoteSnapshot?.status ?? draft.status}</Text>
            </View>
          </View>
          {remoteSnapshot ? (
            <Text style={styles.helperText}>
              Dernière synchro : {new Date(remoteSnapshot.updated_at).toLocaleString('fr-FR')}
            </Text>
          ) : null}
          {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Configuration de la partie</Text>
          <Field label="Titre de la partie" value={draft.settings.game_title} onChangeText={updateTitle} />

          <View style={styles.switchRow}>
            <Text style={styles.inputLabel}>Manches aléatoires</Text>
            <Switch
              value={draft.settings.random_round_order}
              onValueChange={updateRandomOrder}
              trackColor={{ false: '#4b5563', true: '#16a34a' }}
              thumbColor="#f8fafc"
            />
          </View>

          <Field
            label="Nombre de manches blindtest"
            keyboardType="number-pad"
            value={String(draft.games[0]?.round_count ?? 1)}
            onChangeText={updateRoundCount}
          />

          <View style={styles.switchRow}>
            <Text style={styles.inputLabel}>Buzzers activés</Text>
            <Switch
              value={blindtestRound?.buzzer_enabled ?? true}
              onValueChange={updateBuzzerEnabled}
              trackColor={{ false: '#4b5563', true: '#16a34a' }}
              thumbColor="#f8fafc"
            />
          </View>
        </View>

        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Équipes</Text>
            <Pressable style={styles.secondaryButton} onPress={addTeam} disabled={teams.length >= 6}>
              <Text style={styles.secondaryButtonText}>Ajouter</Text>
            </Pressable>
          </View>
          <Text style={styles.helperText}>Définis la touche clavier ou le bouton USB (HID) envoyée par équipe sur Mac/PC.</Text>

          {teams.map((team, index) => (
            <View key={`${team}-${index}`} style={styles.teamRow}>
              <Field label={`Équipe ${index + 1}`} value={team} onChangeText={(value) => updateTeam(index, value)} />
              <Field
                label="Touche buzzer / USB"
                value={buzzerKeys[index] ?? ''}
                onChangeText={(value) => updateBuzzerKey(index, value)}
                placeholder={defaultBuzzerKey(index)}
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
            <Text style={styles.summaryValue}>{summary.teamsCount}</Text>
          </View>
          <View>
            <Text style={styles.summaryLabel}>Manches</Text>
            <Text style={styles.summaryValue}>{summary.roundCount}</Text>
          </View>
          <View>
            <Text style={styles.summaryLabel}>Playlist</Text>
            <Text style={styles.summaryValue}>{summary.playlistCount}</Text>
          </View>
        </View>

        <Pressable style={styles.primaryButton} onPress={validateGame}>
          <Text style={styles.primaryButtonText}>Valider</Text>
        </Pressable>

        <View style={styles.sectionCard}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Playlist blindtest</Text>
            <Pressable style={styles.secondaryButton} onPress={addPlaylistTrack}>
              <Text style={styles.secondaryButtonText}>Ajouter une musique</Text>
            </Pressable>
          </View>

          <Field
            label="URL / ID Spotify"
            value={spotifyPlaylistUrl}
            onChangeText={setSpotifyPlaylistUrl}
            placeholder="https://open.spotify.com/playlist/..."
          />

          <View style={styles.actionRowWrap}>
            <Pressable style={styles.secondaryButton} onPress={importSpotifyPlaylist}>
              <Text style={styles.secondaryButtonText}>Importer depuis Spotify</Text>
            </Pressable>
            {blindtestState?.playlist_source_url ? (
              <Pressable style={styles.ghostButton} onPress={() => openExternalUrl(blindtestState.playlist_source_url)}>
                <Text style={styles.ghostButtonText}>Ouvrir la playlist</Text>
              </Pressable>
            ) : null}
          </View>

          {blindtestState?.playlist_name ? (
            <View style={styles.spotifyInfoCard}>
              <Text style={styles.roundTitle}>{blindtestState.playlist_name}</Text>
              <Text style={styles.helperText}>Source : {blindtestState.playlist_provider || 'manual'}</Text>
              <Text style={styles.helperText}>Musiques chargées : {blindtestState.total_tracks}</Text>
            </View>
          ) : null}

          {playlistTracks.map((track, index) => (
            <View key={`${track.title}-${index}`} style={styles.roundCard}>
              <Text style={styles.roundTitle}>Musique {index + 1}</Text>
              <Field label="Titre" value={track.title} onChangeText={(value) => updatePlaylistTrack(index, 'title', value)} />
              <Field label="Artiste" value={track.artist} onChangeText={(value) => updatePlaylistTrack(index, 'artist', value)} />
              <Field label="URL preview" value={track.preview_url} onChangeText={(value) => updatePlaylistTrack(index, 'preview_url', value)} />
              <Field label="Artwork URL" value={track.artwork_url} onChangeText={(value) => updatePlaylistTrack(index, 'artwork_url', value)} />
            </View>
          ))}

          <View style={styles.actionRow}>
            <Pressable style={styles.secondaryButton} onPress={loadPlaylist}>
              <Text style={styles.secondaryButtonText}>Charger la playlist</Text>
            </Pressable>
            <Pressable style={styles.primaryButtonCompact} onPress={launchGame}>
              <Text style={styles.primaryButtonText}>Démarrer</Text>
            </Pressable>
          </View>
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Blindtest en direct</Text>
          <Text style={styles.helperText}>
            {blindtestState
              ? `Musique ${blindtestState.current_track_index}/${Math.max(blindtestState.total_tracks, 1)} • reste ${blindtestState.tracks_remaining}`
              : 'La partie n’est pas encore lancée.'}
          </Text>

          <View style={styles.liveCard}>
            <Text style={styles.nowPlayingLabel}>Lecture</Text>
            <Text style={styles.nowPlayingTitle}>{activeTrack?.title ?? 'Titre masqué'}</Text>
            <Text style={styles.nowPlayingArtist}>{activeTrack?.artist ?? 'Artiste masqué'}</Text>
            <Text style={styles.helperText}>État : {blindtestState?.playback_state ?? 'stopped'}</Text>
            <Text style={styles.helperText}>Dernier buzzer : {blindtestState?.current_buzzer_team ?? '—'}</Text>
            <Text style={styles.helperText}>Mode audio : {getBlindtestAudioModeLabel(audioMode)}</Text>
            {activeTrack?.track_id ? (
              <View style={styles.spotifyConnectCard}>
                <Text style={styles.spotifyConnectTitle}>Spotify Premium</Text>
                <Text style={styles.helperText}>
                  La lecture complète nécessite un compte Premium et un appareil Spotify actif.
                </Text>
                <View style={styles.actionRowWrap}>
                  {!spotifyPlayer.isAuthenticated ? (
                    <Pressable
                      style={[styles.secondaryButton, (!spotifyPlayer.isConfigured || spotifyPlayer.isAuthenticating || spotifyPlayer.isBusy) && styles.disabledButton]}
                      onPress={() => void spotifyPlayer.controls.login()}
                      disabled={!spotifyPlayer.isConfigured || spotifyPlayer.isAuthenticating || spotifyPlayer.isBusy}
                    >
                      <Text style={styles.secondaryButtonText}>
                        {spotifyPlayer.isAuthenticating || spotifyPlayer.isBusy ? 'Connexion…' : 'Connecter Spotify'}
                      </Text>
                    </Pressable>
                  ) : (
                    <>
                      <Pressable style={styles.secondaryButton} onPress={() => void spotifyPlayer.controls.refreshDevices()}>
                        <Text style={styles.secondaryButtonText}>Actualiser les appareils</Text>
                      </Pressable>
                      <Pressable style={styles.ghostButton} onPress={() => void spotifyPlayer.controls.logout()}>
                        <Text style={styles.ghostButtonText}>Déconnecter</Text>
                      </Pressable>
                    </>
                  )}
                  <Pressable style={styles.ghostButton} onPress={() => void openSpotifyTrackInApp()}>
                    <Text style={styles.ghostButtonText}>Ouvrir dans Spotify</Text>
                  </Pressable>
                </View>
                {spotifyPlayer.selectedDeviceName ? (
                  <Text style={styles.helperText}>Appareil actif : {spotifyPlayer.selectedDeviceName}</Text>
                ) : null}
                {spotifyPlayer.devices.length ? (
                  <View style={styles.deviceListWrap}>
                    {spotifyPlayer.devices.map((device) => (
                      <Pressable
                        key={device.id}
                        style={[
                          styles.deviceChip,
                          spotifyPlayer.selectedDeviceId === device.id && styles.deviceChipActive,
                        ]}
                        onPress={() => spotifyPlayer.controls.setSelectedDeviceId(device.id)}
                      >
                        <Text style={styles.deviceChipText}>{device.name}</Text>
                        <Text style={styles.deviceChipMeta}>{device.type}</Text>
                      </Pressable>
                    ))}
                  </View>
                ) : null}
              </View>
            ) : null}
            <Text style={styles.helperText}>
              Progression : {formatDuration(audioPlayer.positionMs)} / {formatDuration(audioPlayer.durationMs)}
            </Text>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${Math.round(audioPlayer.progressRatio * 100)}%` }]} />
            </View>
            <View style={styles.actionRowWrap}>
              <Pressable
                style={[styles.ghostButton, !canControlPlaybackActions && styles.disabledButton]}
                onPress={() => void playCurrentTrack()}
                disabled={!canControlPlaybackActions}
              >
                <Text style={styles.ghostButtonText}>Play</Text>
              </Pressable>
              <Pressable
                style={[styles.ghostButton, !canControlPlaybackActions && styles.disabledButton]}
                onPress={() => void pauseCurrentTrack()}
                disabled={!canControlPlaybackActions}
              >
                <Text style={styles.ghostButtonText}>Pause</Text>
              </Pressable>
              <Pressable
                style={[styles.ghostButton, !canControlPlaybackActions && styles.disabledButton]}
                onPress={() => void resumeCurrentTrack()}
                disabled={!canControlPlaybackActions}
              >
                <Text style={styles.ghostButtonText}>Reprendre</Text>
              </Pressable>
              <Pressable
                style={[styles.ghostButton, !canControlPlaybackActions && styles.disabledButton]}
                onPress={() => void stopCurrentTrack()}
                disabled={!canControlPlaybackActions}
              >
                <Text style={styles.ghostButtonText}>Stop</Text>
              </Pressable>
              {audioMode === 'spotify-app' ? (
                <Pressable style={styles.secondaryButton} onPress={() => void openSpotifyTrackInApp()}>
                  <Text style={styles.secondaryButtonText}>Ouvrir dans Spotify</Text>
                </Pressable>
              ) : null}
            </View>
            <View style={styles.actionRowWrap}>
              {activeTrack?.preview_url ? (
                <Pressable style={styles.ghostButton} onPress={() => openExternalUrl(activeTrack.preview_url)}>
                  <Text style={styles.ghostButtonText}>Écouter la preview</Text>
                </Pressable>
              ) : null}
              {blindtestState?.playlist_source_url ? (
                <Pressable style={styles.ghostButton} onPress={() => openExternalUrl(blindtestState.playlist_source_url)}>
                  <Text style={styles.ghostButtonText}>Voir la playlist</Text>
                </Pressable>
              ) : null}
            </View>
          </View>

          <View style={styles.keyMapWrap}>
            {teams.map((team, index) => (
              <View key={`${team}-binding`} style={styles.keyChip}>
                <Text style={styles.keyChipLabel}>{team}</Text>
                <Text style={styles.keyChipValue}>{buzzerKeys[index] ?? defaultBuzzerKey(index)}</Text>
              </View>
            ))}
          </View>

          <View style={styles.scoreGrid}>
            {teams.map((team) => (
              <Pressable key={team} style={styles.scoreTile} onPress={() => socket.buzz(team)}>
                <Text style={styles.scoreTileLabel}>{team}</Text>
                <Text style={styles.scoreTileValue}>{blindtestState?.scores?.[team] ?? 0}</Text>
                <Text style={styles.scoreTileHint}>Buzz test</Text>
              </Pressable>
            ))}
          </View>

          <View style={styles.actionRowWrap}>
            <Pressable style={[styles.primaryButtonCompact, styles.successButton]} onPress={() => markAnswer(true)}>
              <Text style={styles.primaryButtonText}>Vrai / Volume +</Text>
            </Pressable>
            <Pressable style={[styles.primaryButtonCompact, styles.falseButton]} onPress={() => markAnswer(false)}>
              <Text style={styles.primaryButtonText}>Faux / Volume -</Text>
            </Pressable>
            <Pressable style={styles.primaryButtonCompact} onPress={nextTrack}>
              <Text style={styles.primaryButtonText}>Musique suivante</Text>
            </Pressable>
          </View>

          {blindtestState?.winner_team ? <Text style={styles.winnerText}>Gagnant de la manche : {blindtestState.winner_team}</Text> : null}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

type FieldProps = {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
  keyboardType?: 'default' | 'number-pad';
  placeholder?: string;
};

function Field({ label, value, onChangeText, keyboardType = 'default', placeholder }: FieldProps) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.inputLabel}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType={keyboardType}
        autoCapitalize="none"
        autoCorrect={false}
        placeholder={placeholder}
        placeholderTextColor="#7c8aa0"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#08111d',
  },
  container: {
    padding: 16,
    gap: 16,
    backgroundColor: '#08111d',
  },
  heroCard: {
    backgroundColor: '#0f2030',
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  eyebrow: {
    color: '#22c55e',
    textTransform: 'uppercase',
    letterSpacing: 1.5,
    marginBottom: 8,
    fontWeight: '700',
  },
  title: {
    color: '#f8fafc',
    fontSize: 28,
    fontWeight: '800',
  },
  subtitle: {
    color: '#9db0c4',
    marginTop: 8,
    lineHeight: 22,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 16,
  },
  badge: {
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  badgeSuccess: {
    backgroundColor: 'rgba(34,197,94,0.2)',
  },
  badgeWarning: {
    backgroundColor: 'rgba(245,158,11,0.2)',
  },
  badgeText: {
    color: '#f8fafc',
    textTransform: 'uppercase',
    fontWeight: '700',
    fontSize: 12,
  },
  helperText: {
    color: '#9db0c4',
    marginTop: 12,
  },
  errorText: {
    color: '#fda4af',
    marginTop: 12,
    fontWeight: '600',
  },
  sectionCard: {
    backgroundColor: '#0f1724',
    borderRadius: 24,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
    gap: 12,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  sectionTitle: {
    color: '#f8fafc',
    fontSize: 20,
    fontWeight: '700',
  },
  fieldWrap: {
    gap: 8,
    flex: 1,
  },
  inputLabel: {
    color: '#cbd5e1',
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#13283c',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    color: '#f8fafc',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  secondaryButton: {
    backgroundColor: 'rgba(34,197,94,0.18)',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
  },
  ghostButton: {
    backgroundColor: 'rgba(255,255,255,0.06)',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  disabledButton: {
    opacity: 0.45,
  },
  secondaryButtonText: {
    color: '#bbf7d0',
    fontWeight: '700',
  },
  ghostButtonText: {
    color: '#f8fafc',
    fontWeight: '700',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  teamRow: {
    gap: 10,
  },
  keyMapWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  keyChip: {
    backgroundColor: '#122235',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
    minWidth: 120,
  },
  keyChipLabel: {
    color: '#9db0c4',
    fontSize: 12,
    fontWeight: '700',
  },
  keyChipValue: {
    color: '#f8fafc',
    marginTop: 6,
    fontSize: 18,
    fontWeight: '800',
    textTransform: 'uppercase',
  },
  removeText: {
    color: '#fda4af',
    fontWeight: '700',
  },
  removeTextDisabled: {
    opacity: 0.35,
  },
  summaryCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#0f2030',
    borderRadius: 24,
    padding: 18,
    gap: 12,
  },
  summaryLabel: {
    color: '#9db0c4',
    marginBottom: 6,
  },
  summaryValue: {
    color: '#f8fafc',
    fontSize: 22,
    fontWeight: '800',
  },
  primaryButton: {
    backgroundColor: '#22c55e',
    borderRadius: 18,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 4,
  },
  primaryButtonCompact: {
    backgroundColor: '#22c55e',
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 18,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#041019',
    fontWeight: '800',
    fontSize: 16,
  },
  roundCard: {
    backgroundColor: '#122235',
    borderRadius: 18,
    padding: 14,
    gap: 12,
  },
  spotifyInfoCard: {
    backgroundColor: '#122235',
    borderRadius: 18,
    padding: 14,
    gap: 4,
  },
  spotifyConnectCard: {
    backgroundColor: 'rgba(34,197,94,0.08)',
    borderRadius: 18,
    padding: 14,
    gap: 8,
    borderWidth: 1,
    borderColor: 'rgba(34,197,94,0.15)',
    marginTop: 12,
  },
  spotifyConnectTitle: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '800',
  },
  roundTitle: {
    color: '#f8fafc',
    fontSize: 17,
    fontWeight: '700',
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  actionRowWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  progressTrack: {
    width: '100%',
    height: 10,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.08)',
    overflow: 'hidden',
    marginTop: 6,
  },
  progressFill: {
    height: '100%',
    borderRadius: 999,
    backgroundColor: '#22c55e',
  },
  deviceListWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 8,
  },
  deviceChip: {
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
    minWidth: 120,
  },
  deviceChipActive: {
    borderColor: 'rgba(34,197,94,0.5)',
    backgroundColor: 'rgba(34,197,94,0.14)',
  },
  deviceChipText: {
    color: '#f8fafc',
    fontWeight: '700',
  },
  deviceChipMeta: {
    color: '#9db0c4',
    marginTop: 4,
    fontSize: 12,
  },
  liveCard: {
    backgroundColor: '#122235',
    borderRadius: 20,
    padding: 16,
    gap: 6,
  },
  nowPlayingLabel: {
    color: '#9db0c4',
    textTransform: 'uppercase',
    letterSpacing: 1.1,
    fontWeight: '700',
  },
  nowPlayingTitle: {
    color: '#f8fafc',
    fontSize: 24,
    fontWeight: '800',
  },
  nowPlayingArtist: {
    color: '#cbd5e1',
    fontSize: 16,
    fontWeight: '600',
  },
  scoreGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  scoreTile: {
    flexBasis: '48%',
    flexGrow: 1,
    backgroundColor: '#122235',
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.06)',
  },
  scoreTileLabel: {
    color: '#cbd5e1',
    fontWeight: '700',
  },
  scoreTileValue: {
    color: '#f8fafc',
    fontSize: 28,
    fontWeight: '800',
    marginTop: 10,
  },
  scoreTileHint: {
    color: '#9db0c4',
    marginTop: 6,
  },
  successButton: {
    backgroundColor: '#16a34a',
  },
  falseButton: {
    backgroundColor: '#ef4444',
  },
  winnerText: {
    color: '#bbf7d0',
    fontWeight: '800',
    fontSize: 16,
    marginTop: 8,
  },
});


