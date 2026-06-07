import { Linking } from 'react-native';
import { BlindtestTrack } from '../../types/gameConfig';

export type BlindtestAudioMode = 'preview-native' | 'spotify-full' | 'spotify-app' | 'unavailable';

export const resolveBlindtestAudioMode = (
  track: BlindtestTrack | null | undefined,
  options?: { spotifyConnected?: boolean },
): BlindtestAudioMode => {
  if (!track) {
    return 'unavailable';
  }
  if (track.track_id.trim() && options?.spotifyConnected) {
    return 'spotify-full';
  }
  if (track.preview_url.trim()) {
    return 'preview-native';
  }
  if (track.track_id.trim()) {
    return 'spotify-app';
  }
  return 'unavailable';
};

export const getBlindtestAudioModeLabel = (mode: BlindtestAudioMode): string => {
  if (mode === 'preview-native') {
    return 'Preview native intégrée';
  }
  if (mode === 'spotify-full') {
    return 'Spotify Premium connecté';
  }
  if (mode === 'spotify-app') {
    return 'Bascule vers Spotify';
  }
  return 'Lecture indisponible';
};

export const buildSpotifyTrackUri = (trackId: string): string => `spotify:track:${trackId.trim()}`;

export const buildSpotifyTrackWebUrl = (trackId: string): string => `https://open.spotify.com/track/${trackId.trim()}`;

export const openSpotifyTrack = async (track: BlindtestTrack | null | undefined): Promise<void> => {
  const trackId = track?.track_id?.trim() ?? '';
  if (!trackId) {
    throw new Error('Aucune piste Spotify disponible.');
  }

  const nativeUri = buildSpotifyTrackUri(trackId);
  const webUrl = buildSpotifyTrackWebUrl(trackId);

  const canOpenNative = await Linking.canOpenURL(nativeUri);
  if (canOpenNative) {
    await Linking.openURL(nativeUri);
    return;
  }

  await Linking.openURL(webUrl);
};


