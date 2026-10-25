import { StyleSheet, Text, View } from 'react-native';
import { colors, styles } from '../theme';

export type ScoreHighlight = { team: string; tone: 'good' | 'bad' } | null;

type Props = {
  teams: string[];
  scores: Record<string, number>;
  goal: number;
  unit: string;
  highlight?: ScoreHighlight;
  winnerTeam?: string | null;
};

// Scores des jeux « premier à N » : une pastille par point sous le nom de l'équipe.
export function RaceScoreCard({ teams, scores, goal, unit, highlight = null, winnerTeam = null }: Props) {
  return (
    <View style={styles.sectionCard}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Scores</Text>
        <Text style={local.goal}>Objectif {goal}</Text>
      </View>
      {teams.map((team) => {
        const score = scores[team] ?? 0;
        const tone = highlight?.team === team ? highlight.tone : null;
        return (
          <View
            key={team}
            style={[styles.rankRow, (team === winnerTeam || tone === 'good') && styles.rankRowWinner, tone === 'bad' && local.rowBad]}
            accessible
            accessibilityLabel={`${team} : ${score} ${unit}${score > 1 ? 's' : ''} sur ${goal}`}
          >
            <View style={local.team}>
              <Text style={styles.rankTeam} numberOfLines={1}>{team}</Text>
              <View style={local.dots}>
                {Array.from({ length: goal }, (_, index) => (
                  <View key={index} style={[local.dot, index < score && local.dotFilled]} />
                ))}
              </View>
            </View>
            <Text style={local.score}>{score}</Text>
          </View>
        );
      })}
    </View>
  );
}

const local = StyleSheet.create({
  goal: { color: colors.accent, fontWeight: '900' },
  rowBad: { backgroundColor: 'rgba(239,68,68,0.16)', borderColor: colors.danger },
  team: { flex: 1, gap: 8 },
  dots: { flexDirection: 'row', flexWrap: 'wrap', gap: 5 },
  dot: { width: 10, height: 10, borderRadius: 5, backgroundColor: 'rgba(255,255,255,0.12)' },
  dotFilled: { backgroundColor: colors.accent },
  score: { color: colors.text, fontSize: 24, fontWeight: '900', minWidth: 28, textAlign: 'right', fontVariant: ['tabular-nums'] },
});
