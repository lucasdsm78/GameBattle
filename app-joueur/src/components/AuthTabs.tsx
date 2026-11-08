import { KeyboardEvent, useRef } from 'react';

type Props<T extends string> = {
  tabs: readonly { value: T; label: string }[];
  selected: T;
  onSelect: (value: T) => void;
  panelId: string;
  idPrefix: string;
  label: string;
  disabled?: boolean;
};

export const tabId = (idPrefix: string, value: string) => `${idPrefix}-tab-${value}`;

/** Onglets WAI-ARIA : flèches, Début et Fin déplacent la sélection, une seule tabulation pour tout le groupe. */
export function AuthTabs<T extends string>({ tabs, selected, onSelect, panelId, idPrefix, label, disabled }: Props<T>) {
  const buttons = useRef(new Map<T, HTMLButtonElement>());

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = tabs.findIndex((tab) => tab.value === selected);
    const next = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabs.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    const target = tabs[(next + tabs.length) % tabs.length].value;
    onSelect(target);
    buttons.current.get(target)?.focus();
  }

  return (
    <div className="auth-tabs" role="tablist" aria-label={label} onKeyDown={onKeyDown}>
      {tabs.map((tab) => (
        <button
          key={tab.value}
          ref={(node) => {
            if (node) buttons.current.set(tab.value, node);
            else buttons.current.delete(tab.value);
          }}
          id={tabId(idPrefix, tab.value)}
          type="button"
          role="tab"
          className="auth-tab"
          aria-selected={tab.value === selected}
          aria-controls={panelId}
          tabIndex={tab.value === selected ? 0 : -1}
          onClick={() => onSelect(tab.value)}
          disabled={disabled}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
