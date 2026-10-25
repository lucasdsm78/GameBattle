// Drapeaux SVG livrés avec l'app (aucune requête externe) : chaque fichier n'est chargé qu'à l'affichage.
const FLAG_URLS = import.meta.glob<string>('/node_modules/country-flag-icons/3x2/*.svg', {
  eager: true,
  query: '?url',
  import: 'default',
});

const FLAG_CODE = /^[A-Z]{2}$/;

export function flagUrl(code: string): string | undefined {
  return FLAG_CODE.test(code) ? FLAG_URLS[`/node_modules/country-flag-icons/3x2/${code}.svg`] : undefined;
}

// Le bon drapeau doit s'afficher sans délai : on met tout le catalogue en cache dès l'arrivée sur le jeu.
let preloaded = false;
export function preloadFlags(): void {
  if (preloaded) return;
  preloaded = true;
  for (const url of Object.values(FLAG_URLS)) {
    const image = new Image();
    image.decoding = 'async';
    image.src = url;
  }
}
