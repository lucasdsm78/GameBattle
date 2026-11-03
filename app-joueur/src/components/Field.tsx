import { ReactNode } from 'react';

type Props = {
  id: string;
  label: string;
  hint?: ReactNode;
  error?: string | null;
  children: ReactNode;
};

/** Identifiant du texte d'aide d'un champ, à passer à `aria-describedby` sur l'entrée. */
export const helpId = (id: string) => `${id}-help`;

/** Libellé, entrée et texte d'aide ; l'erreur remplace l'aide au même endroit pour que la mise en page ne saute pas. */
export function Field({ id, label, hint, error, children }: Props) {
  return (
    <div className="field">
      <label htmlFor={id} className="field-label">
        {label}
      </label>
      {children}
      <p id={helpId(id)} className={error ? 'field-error' : 'field-hint'}>
        {error ?? hint}
      </p>
    </div>
  );
}
