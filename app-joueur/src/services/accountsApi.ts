import { ApiError, isObject, postJson, readJson, send } from './http';

export { ApiError } from './http';

export type Account = { pseudo: string };
export type Credentials = { pseudo: string; password: string };
export type CredentialField = keyof Credentials;

const BASE_URL = '/api/accounts';

export const isCredentialField = (value: unknown): value is CredentialField => value === 'pseudo' || value === 'password';

/** Une réponse sans pseudo valide est une erreur : jamais de joueur « connecté » sans nom. */
const isAccount = (body: unknown): body is Account => isObject(body) && typeof body.pseudo === 'string' && body.pseudo.length > 0;
const readAccount = async (response: Response): Promise<Account> => ({ pseudo: (await readJson(response, isAccount)).pseudo });

export const accountsApi = {
  /** Le joueur de la session en cours, ou `null` s'il n'est pas connecté. */
  async me(signal?: AbortSignal): Promise<Account | null> {
    try {
      return await readAccount(await send(`${BASE_URL}/me`, { signal }));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) return null;
      throw error;
    }
  },
  login: (credentials: Credentials) => postJson(`${BASE_URL}/login`, credentials).then(readAccount),
  register: (credentials: Credentials) => postJson(`${BASE_URL}/register`, credentials).then(readAccount),
  logout: async (): Promise<void> => {
    await postJson(`${BASE_URL}/logout`);
  },
};
