import Constants from 'expo-constants';

const extra = (Constants.expoConfig?.extra ?? {}) as {
  backendWsUrl?: string;
  controllerToken?: string;
};

export const controllerToken = (): string => extra.controllerToken ?? 'change-me-controller';

// En développement (Expo Go), le backend tourne sur la même machine que Metro : on reprend son IP
// pour ne pas devoir modifier app.json à chaque changement de réseau. Un APK utilise app.json.
export const backendWsBase = (): string => {
  const configured = (extra.backendWsUrl ?? 'ws://localhost:8000').replace(/\/$/, '');
  const metroHost = __DEV__ ? Constants.expoConfig?.hostUri?.split(':')[0] : undefined;
  return metroHost ? configured.replace(/^(wss?:\/\/)[^:/]+/, `$1${metroHost}`) : configured;
};

const SAFE_FILE = /^[a-z0-9-]+\.(png|jpg)$/;

// URL d'une image servie par le backend ; un nom inattendu ne produit jamais de requête.
export function mediaUrl(folder: 'fair-price', fileName: string): string | undefined {
  return SAFE_FILE.test(fileName) ? `${backendWsBase().replace(/^ws/, 'http')}/media/${folder}/${fileName}` : undefined;
}
