import { FormEvent, KeyboardEvent, useEffect, useId, useRef, useState } from 'react';
import { Account, ApiError, CredentialField, Credentials, accountsApi, isCredentialField } from '../services/accountsApi';
import { PSEUDO_MAX_LENGTH, normalizePseudo, passwordProblem, passwordStrength, pseudoProblem } from '../services/accountRules';
import { AuthTabs, tabId } from './AuthTabs';
import { Field, helpId } from './Field';
import { PasswordField } from './PasswordField';

type Mode = 'login' | 'register';
type ServerError = { message: string; field?: CredentialField };

const COPY = {
  login: {
    tab: 'Connexion',
    submit: 'Se connecter',
    pending: 'Connexion…',
    autoComplete: 'current-password',
    pseudoHint: null,
    passwordHint: null,
  },
  register: {
    tab: 'Créer un compte',
    submit: 'Créer mon compte',
    pending: 'Création du compte…',
    autoComplete: 'new-password',
    pseudoHint: '3 à 20 caractères : lettres, chiffres, « - » et « _ ». Il sera visible des autres joueurs.',
    passwordHint: '8 caractères minimum. Une phrase de passe, c’est encore mieux.',
  },
} as const;

const TABS = [
  { value: 'login', label: COPY.login.tab },
  { value: 'register', label: COPY.register.tab },
] as const;

const EMPTY = { pseudo: '', password: '' } satisfies Credentials;
const UNTOUCHED: Record<CredentialField, boolean> = { pseudo: false, password: false };

/** Problème détecté avant envoi. À la connexion, seul un champ vide compte : le serveur ne dit pas lequel est faux. */
function clientProblem(mode: Mode, field: CredentialField, values: Credentials): string | null {
  if (mode === 'login') return values[field] ? null : field === 'pseudo' ? 'Indique ton pseudo.' : 'Indique ton mot de passe.';
  return field === 'pseudo' ? pseudoProblem(values.pseudo) : passwordProblem(values.password, values.pseudo);
}

type Props = { onSignedIn: (account: Account) => void };

export function AuthCard({ onSignedIn }: Props) {
  const [mode, setMode] = useState<Mode>('login');
  const [raw, setRaw] = useState<Credentials>(EMPTY);
  const [touched, setTouched] = useState(UNTOUCHED);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<ServerError | null>(null);
  const pseudoInput = useRef<HTMLInputElement>(null);
  const ids = useId();

  const copy = COPY[mode];
  const registering = mode === 'register';
  const values: Credentials = { pseudo: normalizePseudo(raw.pseudo), password: raw.password };
  const fieldId = (field: CredentialField) => `${ids}-${field}`;
  const strength = passwordStrength(values.password);

  // Après le rendu (les champs sont de nouveau actifs) : le curseur va sur le champ que le serveur a refusé.
  const refusedField = serverError?.field;
  useEffect(() => {
    if (refusedField) document.getElementById(`${ids}-${refusedField}`)?.focus();
  }, [serverError, refusedField, ids]);

  // Une erreur s'affiche à l'envoi, ou dès qu'on quitte le champ à l'inscription ; celle du serveur prime.
  function errorFor(field: CredentialField): string | null {
    if (serverError?.field === field) return serverError.message;
    return submitted || (registering && touched[field]) ? clientProblem(mode, field, values) : null;
  }

  function update(field: CredentialField, value: string) {
    setRaw((current) => ({ ...current, [field]: value }));
    setServerError(null);
  }

  function switchMode(next: Mode) {
    setMode(next);
    setTouched(UNTOUCHED);
    setSubmitted(false);
    setServerError(null);
  }

  // Entrée sur le pseudo passe au mot de passe tant qu'il est vide, au lieu d'envoyer un formulaire incomplet.
  function onPseudoKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' && !values.password) {
      event.preventDefault();
      document.getElementById(fieldId('password'))?.focus();
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    setSubmitted(true);
    setServerError(null);
    const invalidField = (['pseudo', 'password'] as const).find((field) => clientProblem(mode, field, values));
    if (invalidField) {
      document.getElementById(fieldId(invalidField))?.focus();
      return;
    }
    setSubmitting(true);
    try {
      const account = await (registering ? accountsApi.register : accountsApi.login)(values);
      setRaw(EMPTY);
      onSignedIn(account);
    } catch (error) {
      setServerError(
        error instanceof ApiError
          ? { message: error.message, field: isCredentialField(error.field) ? error.field : undefined }
          : { message: 'Une erreur inattendue est survenue. Réessaie.' },
      );
      setSubmitting(false);
    }
  }

  const pseudoError = errorFor('pseudo');
  const passwordError = errorFor('password');
  const bannerError = serverError && !serverError.field ? serverError.message : null;

  return (
    <section className="panel auth-card" aria-label={copy.tab}>
      <AuthTabs
        tabs={TABS}
        selected={mode}
        onSelect={switchMode}
        panelId={`${ids}-panel`}
        idPrefix={ids}
        label="Connexion ou inscription"
        disabled={submitting}
      />

      <form id={`${ids}-panel`} className="auth-form" role="tabpanel" aria-labelledby={tabId(ids, mode)} onSubmit={onSubmit} noValidate>
        <Field id={fieldId('pseudo')} label="Pseudo" hint={copy.pseudoHint} error={pseudoError}>
          <input
            ref={pseudoInput}
            id={fieldId('pseudo')}
            name="username"
            className="field-input"
            value={raw.pseudo}
            onChange={(event) => update('pseudo', event.target.value)}
            onBlur={() => setTouched((current) => ({ ...current, pseudo: true }))}
            onKeyDown={onPseudoKeyDown}
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="next"
            maxLength={PSEUDO_MAX_LENGTH}
            aria-invalid={pseudoError ? true : undefined}
            aria-describedby={helpId(fieldId('pseudo'))}
            disabled={submitting}
            required
          />
        </Field>

        <Field
          id={fieldId('password')}
          label="Mot de passe"
          error={passwordError}
          hint={
            registering ? (
              <>
                {copy.passwordHint}
                {values.password ? <span className="sr-only"> Robustesse : {strength.label}.</span> : null}
              </>
            ) : null
          }
        >
          <PasswordField
            id={fieldId('password')}
            value={raw.password}
            onChange={(value) => update('password', value)}
            onBlur={() => setTouched((current) => ({ ...current, password: true }))}
            autoComplete={copy.autoComplete}
            invalid={passwordError !== null}
            disabled={submitting}
          />
          {registering && values.password ? (
            <div className={`strength strength-${strength.level}`} aria-hidden="true">
              <span />
              <span />
              <span />
              <b>{strength.label}</b>
            </div>
          ) : null}
        </Field>

        <p className="form-error" role="alert">
          {bannerError}
        </p>

        <button type="submit" className="primary-button" disabled={submitting} aria-busy={submitting}>
          {submitting ? copy.pending : copy.submit}
        </button>

        <p className="auth-switch">
          {registering ? 'Déjà un compte ?' : 'Pas encore de compte ?'}{' '}
          <button
            type="button"
            className="link-button"
            onClick={() => {
              switchMode(registering ? 'login' : 'register');
              pseudoInput.current?.focus();
            }}
            disabled={submitting}
          >
            {registering ? 'Se connecter' : 'Créer un compte'}
          </button>
        </p>
      </form>
    </section>
  );
}
