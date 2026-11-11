import { RoomFormat, Visibility } from './roomsApi';

export const VISIBILITY_LABELS: Record<Visibility, string> = { public: 'Publique', private: 'Privée' };

export const formatLabel = (format: RoomFormat, teamCount: number) => (format === 'solo' ? 'Chacun pour soi' : `${teamCount} équipes`);

// Une couleur par équipe, comme les pupitres du plateau (mêmes noms que le serveur).
const TEAM_TONES: Record<string, string> = { Rouges: 'red', Bleus: 'blue', Verts: 'green', Jaunes: 'yellow' };
export const teamTone = (team: string) => `tone-${TEAM_TONES[team] ?? 'neutral'}`;

export const playersLabel = (count: number, capacity: number) => `${count}/${capacity} joueur${capacity > 1 ? 's' : ''}`;

export const freeSeatsLabel = (free: number) => (free > 1 ? `${free} places libres` : '1 place libre');

// Chacun pour soi : une couleur par joueur, dans l'ordre d'arrivée.
const PLAYER_TONES = ['blue', 'red', 'green', 'yellow'];
export const playerTone = (index: number) => `tone-${PLAYER_TONES[index % PLAYER_TONES.length]}`;
