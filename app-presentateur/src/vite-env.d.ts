/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GAMEBATTLE_WS_URL?: string;
  readonly VITE_GAMEBATTLE_DISPLAY_TOKEN?: string;
  readonly VITE_SPOTIFY_CLIENT_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
