import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

// L'API est servie sous la même origine que l'app (proxy ici, Caddy en production) : le cookie de session
// reste `SameSite=Strict` et aucune requête n'est cross-origin.
const apiTarget = process.env.GAMEBATTLE_API_URL ?? 'http://127.0.0.1:8000';
// `changeOrigin: false` garde l'en-tête Host : le backend vérifie que l'Origin de la requête est bien la sienne
// (requêtes HTTP comme poignée de main WebSocket des salons).
const proxy = {
  '/api': { target: apiTarget, changeOrigin: false },
  '/ws': { target: apiTarget, changeOrigin: false, ws: true },
};

// Tout vient du même domaine : aucun script, style ou police tiers, aucun script inline.
// `frame-ancestors` ne vaut qu'en en-tête HTTP : il sera posé par Caddy au déploiement.
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self'",
  "font-src 'self'",
  "img-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'self'",
].join('; ');

/** CSP dans le HTML de production seulement : le serveur de dev de Vite injecte des styles inline pour le rechargement à chaud. */
function contentSecurityPolicy(): Plugin {
  return {
    name: 'gamebattle-content-security-policy',
    apply: 'build',
    // Juste après `charset` (qui doit rester en tête) et avant tout script ou feuille de style.
    transformIndexHtml: (html) =>
      html.replace('<meta charset="UTF-8" />', `$&\n    <meta http-equiv="Content-Security-Policy" content="${CONTENT_SECURITY_POLICY}" />`),
  };
}

export default defineConfig({
  plugins: [react(), contentSecurityPolicy()],
  server: { host: '127.0.0.1', port: 5174, strictPort: true, proxy },
  preview: { host: '127.0.0.1', port: 5174, strictPort: true, proxy },
});
