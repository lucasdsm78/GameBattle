import { ReactNode, useId } from 'react';

export type Choice<T extends string> = { value: T; label: ReactNode; hint?: ReactNode; disabled?: boolean; tone?: string };

type Props<T extends string> = {
  legend: string;
  choices: readonly Choice<T>[];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
  compact?: boolean;
};

/** Choix exclusif en grandes cartes. Boutons radio natifs dessous : flèches, tabulation et lecteurs d'écran sans rien recoder. */
export function ChoiceGroup<T extends string>({ legend, choices, value, onChange, disabled, compact }: Props<T>) {
  const name = useId();
  return (
    <fieldset className={`choice-group${compact ? ' is-compact' : ''}`} disabled={disabled}>
      <legend className="field-label">{legend}</legend>
      <div className="choice-options">
        {choices.map((choice) => (
          <label key={choice.value} className={`choice${choice.tone ? ` ${choice.tone}` : ''}`}>
            <input
              type="radio"
              className="sr-only"
              name={name}
              value={choice.value}
              checked={choice.value === value}
              onChange={() => onChange(choice.value)}
              disabled={choice.disabled}
            />
            <span className="choice-label">{choice.label}</span>
            {choice.hint ? <span className="choice-hint">{choice.hint}</span> : null}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
