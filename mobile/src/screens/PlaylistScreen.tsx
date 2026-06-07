import { useState } from 'react';
import { Linking, Pressable, Text, View } from 'react-native';
import { Field } from '../components/Field';
import { styles } from '../theme';
import { GameConfigSnapshot } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot | null;
  errorMessage: string | null;
  onImport: (playlistUrl: string) => void;
  onValidate: () => void;
  onBack: () => void;
};

export function PlaylistScreen({ snapshot, errorMessage, onImport, onValidate, onBack }: Props) {
  const [playlistUrl, setPlaylistUrl] = useState('');
  const blindtest = snapshot?.session.blindtest;
  const importedFromSpotify = blindtest?.playlist_provider === 'spotify' && blindtest.total_tracks > 0;

  const handleImport = () => {
    const value = playlistUrl.trim();
    if (value.length > 0) {
      onImport(value);
    }
  };

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Retour configuration</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Étape 2</Text>
        <Text style={styles.title}>Playlist Spotify</Text>
        <Text style={styles.subtitle}>
          Ouvre Spotify, copie le lien de partage d’une playlist publique, colle-le ici puis importe.
        </Text>
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Importer une playlist</Text>
        <Field
          label="Lien ou ID de playlist Spotify"
          value={playlistUrl}
          onChangeText={setPlaylistUrl}
          placeholder="https://open.spotify.com/playlist/..."
          autoCapitalize="none"
        />
        <View style={styles.actionRowWrap}>
          <Pressable style={styles.ghostButton} onPress={() => Linking.openURL('spotify://').catch(() => Linking.openURL('https://open.spotify.com'))}>
            <Text style={styles.ghostButtonText}>Ouvrir Spotify</Text>
          </Pressable>
          <Pressable style={styles.secondaryButton} onPress={handleImport}>
            <Text style={styles.secondaryButtonText}>Importer la playlist</Text>
          </Pressable>
        </View>

        {importedFromSpotify ? (
          <View style={styles.importedCard}>
            <Text style={styles.importedName}>{blindtest.playlist_name || 'Playlist Spotify'}</Text>
            <Text style={styles.helperText}>{blindtest.total_tracks} musiques importées ✓</Text>
            {blindtest.playlist_source_url ? (
              <Pressable onPress={() => Linking.openURL(blindtest.playlist_source_url)}>
                <Text style={styles.backButtonText}>Ouvrir la playlist ↗</Text>
              </Pressable>
            ) : null}
          </View>
        ) : (
          <Text style={styles.helperText}>Aucune playlist importée pour l’instant.</Text>
        )}
      </View>

      <Pressable
        style={[styles.primaryButton, !importedFromSpotify && styles.primaryButtonDisabled]}
        onPress={onValidate}
        disabled={!importedFromSpotify}
      >
        <Text style={styles.primaryButtonText}>Valider et démarrer le blindtest</Text>
      </Pressable>
    </>
  );
}
