import { ReactNode, useId } from 'react';

type Props = { question: string; action: string; open: boolean; onToggle: () => void; children: ReactNode };

/** Une option secondaire repliée : une question, un bouton qui déplie la suite (annoncé ouvert ou fermé). */
export function Disclosure({ question, action, open, onToggle, children }: Props) {
  const panelId = useId();
  return (
    <div className={`disclosure${open ? ' is-open' : ''}`}>
      <div className="disclosure-head">
        <span>{question}</span>
        <button type="button" className="tool-button" aria-expanded={open} aria-controls={panelId} onClick={onToggle}>
          {open ? 'Masquer' : action}
        </button>
      </div>
      <div id={panelId} className="disclosure-panel" hidden={!open}>
        {open ? children : null}
      </div>
    </div>
  );
}
