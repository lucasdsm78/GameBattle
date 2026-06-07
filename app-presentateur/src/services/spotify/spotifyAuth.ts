// Spotify Authorization Code + PKCE flow for the browser (no client secret needed).
// Produces a user access token with the `streaming` scope required by the Web Playback SDK.

const CLIENT_ID = (import.meta.env.VITE_SPOTIFY_CLIENT_ID ?? '').trim();
const REDIRECT_URI = `${window.location.origin}/callback`;
const SCOPES = [
  'streaming',
  'user-read-email',
  'user-read-private',
  'user-modify-playback-state',
  'user-read-playback-state',
  // Lecture des pistes de playlist (requis depuis le changement Spotify de février 2026).
  'playlist-read-private',
  'playlist-read-collaborative',
].join(' ');

const AUTHORIZE_ENDPOINT = 'https://accounts.spotify.com/authorize';
const TOKEN_ENDPOINT = 'https://accounts.spotify.com/api/token';

const TOKEN_KEY = 'gamebattle.spotify.token';
const VERIFIER_KEY = 'gamebattle.spotify.verifier';

type StoredToken = {
  access_token: string;
  refresh_token: string;
  expires_at: number; // epoch ms
};

export const isSpotifyConfigured = (): boolean => Boolean(CLIENT_ID);

const randomString = (length: number): string => {
  const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const values = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(values, (value) => possible[value % possible.length]).join('');
};

const base64UrlEncode = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};

const sha256 = async (input: string): Promise<ArrayBuffer> => {
  const data = new TextEncoder().encode(input);
  return crypto.subtle.digest('SHA-256', data);
};

const readToken = (): StoredToken | null => {
  const raw = localStorage.getItem(TOKEN_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as StoredToken;
    if (!parsed.access_token) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
};

const writeToken = (token: StoredToken | null): void => {
  if (!token) {
    localStorage.removeItem(TOKEN_KEY);
    return;
  }
  localStorage.setItem(TOKEN_KEY, JSON.stringify(token));
};

export const hasStoredSpotifyToken = (): boolean => readToken() !== null;

export const beginSpotifyLogin = async (): Promise<void> => {
  if (!CLIENT_ID) {
    throw new Error('VITE_SPOTIFY_CLIENT_ID manquant dans app-presentateur/.env');
  }
  const verifier = randomString(64);
  const challenge = base64UrlEncode(await sha256(verifier));
  sessionStorage.setItem(VERIFIER_KEY, verifier);

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: 'code',
    redirect_uri: REDIRECT_URI,
    scope: SCOPES,
    code_challenge_method: 'S256',
    code_challenge: challenge,
  });
  window.location.assign(`${AUTHORIZE_ENDPOINT}?${params.toString()}`);
};

const normalizeTokenResponse = (payload: Record<string, unknown>, previousRefresh = ''): StoredToken => {
  const expiresIn = Number(payload.expires_in ?? 3600);
  return {
    access_token: String(payload.access_token ?? ''),
    refresh_token: String(payload.refresh_token ?? previousRefresh),
    expires_at: Date.now() + Math.max(expiresIn, 60) * 1000,
  };
};

// An authorization code can only be exchanged ONCE. React 18 StrictMode runs
// effects twice in dev, so we cache the in-flight exchange at the module level to
// guarantee a single token request even across StrictMode unmount/remount.
let exchangePromise: Promise<boolean> | null = null;

const exchangeAuthorizationCode = async (): Promise<boolean> => {
  const url = new URL(window.location.href);
  const code = url.searchParams.get('code');
  const error = url.searchParams.get('error');
  if (error) {
    throw new Error(`Spotify a refusé la connexion : ${error}`);
  }
  if (!code) {
    return false;
  }
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!verifier) {
    throw new Error('Vérificateur PKCE introuvable. Relance la connexion Spotify.');
  }

  const body = new URLSearchParams({
    client_id: CLIENT_ID,
    grant_type: 'authorization_code',
    code,
    redirect_uri: REDIRECT_URI,
    code_verifier: verifier,
  });
  const response = await fetch(TOKEN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Échec de l’échange du code Spotify (${response.status}). ${detail}`.trim());
  }
  const payload = (await response.json()) as Record<string, unknown>;
  writeToken(normalizeTokenResponse(payload));
  sessionStorage.removeItem(VERIFIER_KEY);
  return true;
};

// Exchanges the `code` returned on the /callback redirect for tokens.
// Returns true if a token was obtained. Safe to call multiple times (idempotent).
export const completeSpotifyLogin = async (): Promise<boolean> => {
  if (!exchangePromise) {
    exchangePromise = exchangeAuthorizationCode();
  }
  return exchangePromise;
};

const refreshAccessToken = async (token: StoredToken): Promise<StoredToken | null> => {
  if (!token.refresh_token) {
    return null;
  }
  const body = new URLSearchParams({
    client_id: CLIENT_ID,
    grant_type: 'refresh_token',
    refresh_token: token.refresh_token,
  });
  const response = await fetch(TOKEN_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) {
    writeToken(null);
    return null;
  }
  const payload = (await response.json()) as Record<string, unknown>;
  const refreshed = normalizeTokenResponse(payload, token.refresh_token);
  writeToken(refreshed);
  return refreshed;
};

// Returns a valid access token, refreshing if needed. Null if not connected.
export const getValidSpotifyAccessToken = async (): Promise<string | null> => {
  const token = readToken();
  if (!token) {
    return null;
  }
  if (Date.now() < token.expires_at - 30_000) {
    return token.access_token;
  }
  const refreshed = await refreshAccessToken(token);
  return refreshed?.access_token ?? null;
};

export const logoutSpotify = (): void => {
  writeToken(null);
  sessionStorage.removeItem(VERIFIER_KEY);
};
