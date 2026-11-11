import { RoomFormat, Visibility } from './roomsApi';

export const VISIBILITY_LABELS: Record<Visibility, string> = { public: 'Publique', private: 'Privée' };

export const formatLabel = (format: RoomFormat, teamCount: number) => (format === 'solo' ? '1 contre 1' : `${teamCount} équipes`);

// Une couleur par équipe, comme les pupitres du plateau (mêmes noms que le serveur).
const TEAM_TONES: Record<string, string> = { Rouges: 'red', Bleus: 'blue', Verts: 'green', Jaunes: 'yellow' };
export const teamTone = (team: string) => `tone-${TEAM_TONES[team] ?? 'neutral'}`;

export const playersLabel = (count: number, capacity: number) => `${count}/${capacity} joueur${capacity > 1 ? 's' : ''}`;
