export type Account = { pseudo: string };
export type Credentials = { pseudo: string; password: string };
export type CredentialField = keyof Credentials;

/** Erreur à afficher telle quelle (le backend rédige ses messages pour le joueur), sous `field` s'il est connu. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly field?: CredentialField,
  ) {
    super(message);
  }
}

// Même origine que l'app (proxy Vite en dev, Caddy en production) : le cookie de session HttpOnly suit tout seul.
const BASE_URL = '/api/accounts';
const NETWORK_ERROR = 'Le serveur ne répond pas. Vérifie ta connexion et réessaie.';

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}) },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(NETWORK_ERROR, 0);
  }
  if (!response.ok) throw await toApiError(response);
  return response;
}

const isField = (value: unknown): value is CredentialField => value === 'pseudo' || value === 'password';

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as { detail?: unknown; field?: unknown };
    if (typeof body.detail === 'string') return new ApiError(body.detail, response.status, isField(body.field) ? body.field : undefined);
  } catch {
    // Corps absent ou non JSON : message générique ci-dessous.
  }
  const fallback = response.status >= 500 ? 'Le serveur a rencontré un problème. Réessaie dans un instant.' : 'La demande a été refusée.';
  return new ApiError(fallback, response.status);
}

/** Une réponse sans pseudo valide est une erreur : jamais de joueur « connecté » sans nom. */
async function readAccount(response: Response): Promise<Account> {
  const body: unknown = await response.json().catch(() => null);
  if (body && typeof body === 'object' && 'pseudo' in body && typeof body.pseudo === 'string' && body.pseudo.length > 0) {
    return { pseudo: body.pseudo };
  }
  throw new ApiError('Réponse inattendue du serveur. Réessaie dans un instant.', response.status);
}

const post = (path: string, body?: Credentials) => send(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });

export const accountsApi = {
  /** Le joueur de la session en cours, ou `null` s'il n'est pas connecté. */
  async me(signal?: AbortSignal): Promise<Account | null> {
    try {
      return await readAccount(await send('/me', { signal }));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) return null;
      throw error;
    }
  },
  login: (credentials: Credentials) => post('/login', credentials).then(readAccount),
  register: (credentials: Credentials) => post('/register', credentials).then(readAccount),
  logout: async (): Promise<void> => {
    await post('/logout');
  },
};
