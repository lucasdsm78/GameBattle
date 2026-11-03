import { KeyboardEvent, useState } from 'react';
import { PASSWORD_MAX_LENGTH } from '../services/accountRules';
import { helpId } from './Field';

type Props = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onBlur: () => void;
  autoComplete: 'current-password' | 'new-password';
  invalid: boolean;
  disabled: boolean;
};

/** Champ mot de passe : bouton « Afficher » (plutôt qu'une double saisie, pénible sur mobile) et alerte Verr. Maj. */
export function PasswordField({ id, value, onChange, onBlur, autoComplete, invalid, disabled }: Props) {
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const readCapsLock = (event: KeyboardEvent<HTMLInputElement>) => setCapsLock(event.getModifierState('CapsLock'));

  return (
    <>
      <div className="password-field">
        <input
          id={id}
          name="password"
          className="field-input"
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={readCapsLock}
          onKeyUp={readCapsLock}
          onBlur={() => {
            setCapsLock(false);
            onBlur();
          }}
          autoComplete={autoComplete}
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="go"
          maxLength={PASSWORD_MAX_LENGTH}
          aria-invalid={invalid || undefined}
          aria-describedby={helpId(id)}
          disabled={disabled}
          required
        />
        <button
          type="button"
          className="reveal-button"
          onClick={() => setVisible((shown) => !shown)}
          aria-controls={id}
          aria-pressed={visible}
          aria-label={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
          disabled={disabled}
        >
          {visible ? 'Masquer' : 'Afficher'}
        </button>
      </div>
      {capsLock ? (
        <p className="caps-warning" role="status">
          Verr. Maj activé
        </p>
      ) : null}
    </>
  );
}
