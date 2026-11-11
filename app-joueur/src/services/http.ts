/** Erreur à afficher telle quelle (le backend rédige ses messages pour le joueur), sous `field` s'il en désigne un. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly field?: string,
  ) {
    super(message);
  }
}

const NETWORK_ERROR = 'Le serveur ne répond pas. Vérifie ta connexion et réessaie.';
export const UNEXPECTED_RESPONSE = 'Réponse inattendue du serveur. Réessaie dans un instant.';

export const isAbort = (error: unknown) => error instanceof DOMException && error.name === 'AbortError';

/** Message d'erreur affichable, quelle que soit la panne. */
export const errorMessage = (error: unknown, fallback = 'Une erreur inattendue est survenue. Réessaie.') =>
  error instanceof ApiError ? error.message : fallback;

// Même origine que l'app (proxy Vite en dev, Caddy en production) : le cookie de session HttpOnly suit tout seul.
export async function send(url: string, init: RequestInit = {}): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}) },
    });
  } catch (error) {
    if (isAbort(error)) throw error;
    throw new ApiError(NETWORK_ERROR, 0);
  }
  if (!response.ok) throw await toApiError(response);
  return response;
}

export const postJson = (url: string, body?: unknown, signal?: AbortSignal) =>
  send(url, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body), signal });

/** Corps JSON validé par `isValid` : une réponse inattendue est une erreur, jamais un état à moitié rempli. */
export async function readJson<T>(response: Response, isValid: (body: unknown) => body is T): Promise<T> {
  const body: unknown = await response.json().catch(() => null);
  if (isValid(body)) return body;
  throw new ApiError(UNEXPECTED_RESPONSE, response.status);
}

export const isObject = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { detail?: unknown; field?: unknown };
    if (typeof body.detail === 'string') return new ApiError(body.detail, response.status, typeof body.field === 'string' ? body.field : undefined);
  } catch {
    // Corps absent ou non JSON : message générique ci-dessous.
  }
  if (response.status === 429) return new ApiError('Trop de tentatives. Patiente un peu avant de réessayer.', response.status);
  const fallback = response.status >= 500 ? 'Le serveur a rencontré un problème. Réessaie dans un instant.' : 'La demande a été refusée.';
  return new ApiError(fallback, response.status);
}
