// Mêmes règles que le domaine du backend (`domain/accounts`), pour répondre avant tout aller-retour.
// Le serveur reste seul juge : il refuse aussi les mots de passe trop répandus.
export const PSEUDO_MIN_LENGTH = 3;
export const PSEUDO_MAX_LENGTH = 20;
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

const PSEUDO_PATTERN = /^[0-9A-Za-zÀ-ÖØ-öø-ÿ_-]+$/;

export const normalizePseudo = (raw: string): string => raw.trim().normalize('NFC');

export function pseudoProblem(pseudo: string): string | null {
  if (pseudo.length < PSEUDO_MIN_LENGTH || pseudo.length > PSEUDO_MAX_LENGTH) {
    return `Entre ${PSEUDO_MIN_LENGTH} et ${PSEUDO_MAX_LENGTH} caractères.`;
  }
  return PSEUDO_PATTERN.test(pseudo) ? null : 'Lettres, chiffres, « - » et « _ » uniquement.';
}

export function passwordProblem(password: string, pseudo: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) return `Au moins ${PASSWORD_MIN_LENGTH} caractères.`;
  if (password.length > PASSWORD_MAX_LENGTH) return `Au plus ${PASSWORD_MAX_LENGTH} caractères.`;
  if (pseudo.length >= PSEUDO_MIN_LENGTH && password.toLowerCase().includes(pseudo.toLowerCase())) {
    return 'Ton mot de passe ne doit pas contenir ton pseudo.';
  }
  return null;
}

export type PasswordStrength = { level: 0 | 1 | 2 | 3; label: string };

/** Indication pour le joueur : la longueur compte le plus, la variété des caractères un peu. */
export function passwordStrength(password: string): PasswordStrength {
  const kinds = [/[a-zà-ÿ]/, /[A-ZÀ-Þ]/, /\d/, /[^\p{L}\d]/u].filter((pattern) => pattern.test(password)).length;
  const score = password.length + kinds * 2;
  if (password.length < PASSWORD_MIN_LENGTH) return { level: 0, label: 'Trop court' };
  if (score < 16) return { level: 1, label: 'Correct' };
  if (score < 22) return { level: 2, label: 'Solide' };
  return { level: 3, label: 'Excellent' };
}
