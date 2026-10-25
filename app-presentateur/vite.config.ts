import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    // Les drapeaux restent des fichiers à part (chargés à la demande) au lieu d'alourdir le bundle JS.
    assetsInlineLimit: (filePath) => (filePath.includes('country-flag-icons') ? false : undefined),
  },
  server: {
    // Spotify n'accepte plus `localhost` en HTTP pour les redirect URIs — uniquement l'IP loopback 127.0.0.1.
    // On force donc le serveur sur 127.0.0.1 pour que window.location.origin corresponde au redirect enregistré.
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
});

