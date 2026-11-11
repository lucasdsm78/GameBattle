import { useId } from 'react';

type Props = {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
  hint?: string;
  unit: [singular: string, plural: string];
  disabled?: boolean;
};

/** Un nombre à régler du pouce : deux gros boutons − / +, la valeur annoncée aux lecteurs d'écran à chaque changement. */
export function Stepper({ label, value, min, max, onChange, hint, unit, disabled }: Props) {
  const id = useId();
  const [singular, plural] = unit;
  return (
    <div className="field">
      <span id={`${id}-label`} className="field-label">
        {label}
      </span>
      <div className="stepper" role="group" aria-labelledby={`${id}-label`} aria-describedby={hint ? `${id}-hint` : undefined}>
        <button type="button" className="stepper-button" onClick={() => onChange(value - 1)} disabled={disabled || value <= min} aria-label={`Un ${singular} de moins`}>
          −
        </button>
        <output className="stepper-value" aria-live="polite">
          <b>{value}</b> {value > 1 ? plural : singular}
        </output>
        <button type="button" className="stepper-button" onClick={() => onChange(value + 1)} disabled={disabled || value >= max} aria-label={`Un ${singular} de plus`}>
          +
        </button>
      </div>
      {hint ? (
        <p id={`${id}-hint`} className="field-hint">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
