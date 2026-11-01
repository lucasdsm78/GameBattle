// Adresse du backend, partagée par le WebSocket et les images servies par le serveur.
const wsBase = ((import.meta.env.VITE_GAMEBATTLE_WS_URL as string | undefined) ?? 'ws://localhost:8000').replace(/\/$/, '');

export const backendWsBase = (): string => wsBase;

const SAFE_SEGMENT = /^[a-z0-9-]+\.(png|jpg)$/;

// URL d'une image du serveur ; un nom inattendu ne produit jamais de requête.
export function mediaUrl(folder: 'fair-price', fileName: string): string | undefined {
  return SAFE_SEGMENT.test(fileName) ? `${wsBase.replace(/^ws/, 'http')}/media/${folder}/${fileName}` : undefined;
}
