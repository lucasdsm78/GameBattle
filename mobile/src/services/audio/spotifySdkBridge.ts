import Constants from 'expo-constants';
import { NativeModules, Platform } from 'react-native';

export type SpotifySdkBridgeCapabilities = {
  available: boolean;
  isConfigured: boolean;
  redirectUri: string;
  clientId: string;
};

type NativeSpotifySdkModule = {
  initialize(config: { clientId: string; redirectUri: string }): Promise<void>;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  play(trackUri: string, positionMs?: number): Promise<void>;
  pause(): Promise<void>;
  resume(): Promise<void>;
  seek(positionMs: number): Promise<void>;
  getPlayerState(): Promise<{
    isPaused: boolean;
    playbackPosition: number;
    playbackSpeed: number;
    trackUri: string | null;
  } | null>;
};

const extra = (Constants.expoConfig?.extra ?? {}) as {
  spotifyClientId?: string;
  spotifyRedirectScheme?: string;
};

const getNativeModule = (): NativeSpotifySdkModule | null => {
  const nativeModule = NativeModules.GameBattleSpotifySdk as NativeSpotifySdkModule | undefined;
  return nativeModule ?? null;
};

export const getSpotifySdkCapabilities = (): SpotifySdkBridgeCapabilities => {
  const clientId = (extra.spotifyClientId ?? '').trim();
  const scheme = (extra.spotifyRedirectScheme ?? 'gamebattlecontroller').trim() || 'gamebattlecontroller';
  return {
    available: Boolean(getNativeModule()),
    isConfigured: Boolean(clientId),
    redirectUri: `${scheme}://spotify-auth`,
    clientId,
  };
};

export const isSpotifySdkSupportedPlatform = (): boolean => Platform.OS === 'ios' || Platform.OS === 'android';

export const initializeSpotifySdkBridge = async (): Promise<void> => {
  const nativeModule = getNativeModule();
  const capabilities = getSpotifySdkCapabilities();
  if (!nativeModule || !capabilities.isConfigured) {
    throw new Error('Le bridge Spotify SDK natif n’est pas configuré.');
  }
  await nativeModule.initialize({
    clientId: capabilities.clientId,
    redirectUri: capabilities.redirectUri,
  });
};

export const spotifySdkBridge = {
  isAvailable(): boolean {
    return Boolean(getNativeModule()) && isSpotifySdkSupportedPlatform();
  },
  async connect(): Promise<void> {
    const nativeModule = getNativeModule();
    if (!nativeModule) {
      throw new Error('Module Spotify SDK natif indisponible.');
    }
    await nativeModule.connect();
  },
  async disconnect(): Promise<void> {
    const nativeModule = getNativeModule();
    if (!nativeModule) {
      return;
    }
    await nativeModule.disconnect();
  },
  async play(trackUri: string, positionMs = 0): Promise<void> {
    const nativeModule = getNativeModule();
    if (!nativeModule) {
      throw new Error('Module Spotify SDK natif indisponible.');
    }
    await nativeModule.play(trackUri, positionMs);
  },
  async pause(): Promise<void> {
    const nativeModule = getNativeModule();
    if (!nativeModule) {
      throw new Error('Module Spotify SDK natif indisponible.');
    }
    await nativeModule.pause();
  },
  async resume(): Promise<void> {
    const nativeModule = getNativeModule();
    if (!nativeModule) {
      throw new Error('Module Spotify SDK natif indisponible.');
    }
    await nativeModule.resume();
  },
  async seek(positionMs: number): Promise<void> {
    const nativeModule = getNativeModule();
    if (!nativeModule) {
      throw new Error('Module Spotify SDK natif indisponible.');
    }
    await nativeModule.seek(positionMs);
  },
  async getPlayerState(): Promise<{
    isPaused: boolean;
    playbackPosition: number;
    playbackSpeed: number;
    trackUri: string | null;
  } | null> {
    const nativeModule = getNativeModule();
    if (!nativeModule) {
      return null;
    }
    return nativeModule.getPlayerState();
  },
};

