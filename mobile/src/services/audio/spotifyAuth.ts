import Constants from 'expo-constants';
import * as AuthSession from 'expo-auth-session';
import * as SecureStore from 'expo-secure-store';

export type SpotifyTokenSet = {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
};

export type SpotifyAuthConfig = {
  clientId: string;
  redirectScheme: string;
  isConfigured: boolean;
};

const TOKEN_STORAGE_KEY = 'gamebattle.spotify.token-set';

const extra = (Constants.expoConfig?.extra ?? {}) as {
  spotifyClientId?: string;
  spotifyRedirectScheme?: string;
};

export const spotifyDiscovery: AuthSession.DiscoveryDocument = {
  authorizationEndpoint: 'https://accounts.spotify.com/authorize',
  tokenEndpoint: 'https://accounts.spotify.com/api/token',
};

export const getSpotifyAuthConfig = (): SpotifyAuthConfig => {
  const clientId = (extra.spotifyClientId ?? '').trim();
  const redirectScheme = (extra.spotifyRedirectScheme ?? 'gamebattlecontroller').trim() || 'gamebattlecontroller';
  return {
    clientId,
    redirectScheme,
    isConfigured: Boolean(clientId),
  };
};

export const buildSpotifyRedirectUri = (): string => {
  const config = getSpotifyAuthConfig();
  return AuthSession.makeRedirectUri({
    scheme: config.redirectScheme,
    path: 'spotify-auth',
  });
};

export const normalizeSpotifyTokenResponse = (
  response: Pick<AuthSession.TokenResponse, 'accessToken' | 'refreshToken' | 'issuedAt' | 'expiresIn'>,
  previousRefreshToken = '',
): SpotifyTokenSet => {
  const issuedAt = (response.issuedAt ?? Math.floor(Date.now() / 1000)) * 1000;
  const expiresInMs = Math.max((response.expiresIn ?? 3600) * 1000, 60_000);
  return {
    accessToken: response.accessToken,
    refreshToken: response.refreshToken ?? previousRefreshToken,
    expiresAt: issuedAt + expiresInMs,
  };
};

export const storeSpotifyTokenSet = async (tokenSet: SpotifyTokenSet | null): Promise<void> => {
  if (!tokenSet) {
    await SecureStore.deleteItemAsync(TOKEN_STORAGE_KEY);
    return;
  }
  await SecureStore.setItemAsync(TOKEN_STORAGE_KEY, JSON.stringify(tokenSet));
};

export const loadSpotifyTokenSet = async (): Promise<SpotifyTokenSet | null> => {
  const raw = await SecureStore.getItemAsync(TOKEN_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as SpotifyTokenSet;
    if (!parsed.accessToken || !parsed.refreshToken) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
};

export const refreshSpotifyTokenSet = async (tokenSet: SpotifyTokenSet): Promise<SpotifyTokenSet> => {
  const config = getSpotifyAuthConfig();
  if (!config.isConfigured) {
    throw new Error('Spotify n’est pas configuré dans expo.extra.spotifyClientId.');
  }

  const refreshed = await AuthSession.refreshAsync(
    {
      clientId: config.clientId,
      refreshToken: tokenSet.refreshToken,
    },
    spotifyDiscovery,
  );

  return normalizeSpotifyTokenResponse(refreshed, tokenSet.refreshToken);
};

