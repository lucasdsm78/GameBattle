const REGIONAL_INDICATOR_A = 0x1f1e6;
const FLAG_CODE = /^[A-Z]{2}$/;

// Drapeau emoji d'un code ISO 3166-1 alpha-2 (« BR » → 🇧🇷), rendu nativement sur Android et iOS.
export function flagEmoji(code: string): string {
  if (!FLAG_CODE.test(code)) return '🏳️';
  return String.fromCodePoint(...[...code].map((letter) => REGIONAL_INDICATOR_A + letter.charCodeAt(0) - 65));
}
