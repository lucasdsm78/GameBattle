import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
// Polices embarquées (sous-ensemble latin, accents français compris) : aucune requête externe.
import '@fontsource/anton/latin-400.css';
import '@fontsource/barlow-semi-condensed/latin-500.css';
import '@fontsource/barlow-semi-condensed/latin-600.css';
import '@fontsource/barlow-semi-condensed/latin-700.css';
import '@fontsource/barlow-semi-condensed/latin-800.css';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

