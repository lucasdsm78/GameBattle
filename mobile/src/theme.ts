import { StyleSheet } from 'react-native';

export const colors = {
  bg: '#08111d',
  card: '#0f1724',
  cardAlt: '#122235',
  hero: '#0f2030',
  input: '#13283c',
  text: '#f8fafc',
  muted: '#9db0c4',
  subtle: '#cbd5e1',
  accent: '#22c55e',
  accentDark: '#16a34a',
  danger: '#ef4444',
  border: 'rgba(255,255,255,0.08)',
};

export const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.bg },
  scrollView: { flex: 1 },
  container: { padding: 16, gap: 16, backgroundColor: colors.bg, paddingBottom: 48 },

  // Stepper
  stepper: { flexDirection: 'row', gap: 8, marginBottom: 4 },
  stepPill: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.06)',
    alignItems: 'center',
  },
  stepPillActive: { backgroundColor: colors.accent },
  stepPillDone: { backgroundColor: 'rgba(34,197,94,0.25)' },
  stepPillText: { color: colors.subtle, fontWeight: '700', fontSize: 12, textTransform: 'uppercase' },
  stepPillTextActive: { color: colors.bg },

  // Hero / headers
  heroCard: { backgroundColor: colors.hero, borderRadius: 24, padding: 20, borderWidth: 1, borderColor: colors.border },
  eyebrow: { color: colors.accent, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 8, fontWeight: '700' },
  title: { color: colors.text, fontSize: 26, fontWeight: '800' },
  subtitle: { color: colors.muted, marginTop: 8, lineHeight: 22 },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16 },
  badge: { backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8 },
  badgeSuccess: { backgroundColor: 'rgba(34,197,94,0.2)' },
  badgeWarning: { backgroundColor: 'rgba(245,158,11,0.2)' },
  badgeText: { color: colors.text, textTransform: 'uppercase', fontWeight: '700', fontSize: 12 },
  helperText: { color: colors.muted, marginTop: 12 },
  errorText: { color: '#fda4af', marginTop: 12, fontWeight: '600' },

  // Sections / cards
  sectionCard: { backgroundColor: colors.card, borderRadius: 24, padding: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)', gap: 12 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  sectionTitle: { color: colors.text, fontSize: 20, fontWeight: '700' },
  roundCard: { backgroundColor: colors.cardAlt, borderRadius: 18, padding: 14, gap: 12 },
  roundTitle: { color: colors.text, fontSize: 17, fontWeight: '700' },

  // Fields
  fieldWrap: { gap: 8, flex: 1 },
  inputLabel: { color: colors.subtle, fontWeight: '600' },
  input: {
    backgroundColor: colors.input,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    color: colors.text,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },

  // Buttons
  primaryButton: { backgroundColor: colors.accent, borderRadius: 18, paddingVertical: 16, alignItems: 'center' },
  primaryButtonCompact: { backgroundColor: colors.accent, borderRadius: 14, paddingVertical: 14, paddingHorizontal: 18, alignItems: 'center', flexGrow: 1 },
  primaryButtonText: { color: '#041019', fontWeight: '800', fontSize: 16 },
  primaryButtonDisabled: { opacity: 0.4 },
  secondaryButton: { backgroundColor: 'rgba(34,197,94,0.18)', paddingHorizontal: 14, paddingVertical: 10, borderRadius: 12 },
  secondaryButtonText: { color: '#bbf7d0', fontWeight: '700' },
  ghostButton: { backgroundColor: 'rgba(255,255,255,0.06)', paddingHorizontal: 14, paddingVertical: 10, borderRadius: 12, borderWidth: 1, borderColor: colors.border },
  ghostButtonText: { color: colors.text, fontWeight: '700' },
  backButton: { alignSelf: 'flex-start', paddingVertical: 8, paddingHorizontal: 4 },
  backButtonText: { color: colors.muted, fontWeight: '700' },
  successButton: { backgroundColor: colors.accentDark },
  falseButton: { backgroundColor: colors.danger },

  // Switch / rows
  switchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  actionRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  actionRowWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },

  // Game picker
  gamePickerRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  gameChip: {
    flexGrow: 1,
    flexBasis: '45%',
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: 'center',
    backgroundColor: colors.cardAlt,
    borderWidth: 1,
    borderColor: colors.border,
  },
  difficultyChip: {
    flexGrow: 1,
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: colors.cardAlt,
    borderWidth: 1,
    borderColor: colors.border,
  },
  gameChipActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  gameChipText: { color: colors.subtle, fontWeight: '800' },
  gameChipTextActive: { color: colors.bg },

  // Teams
  teamRow: { gap: 10 },
  removeText: { color: '#fda4af', fontWeight: '700' },
  removeTextDisabled: { opacity: 0.35 },

  // Summary
  summaryCard: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: colors.hero, borderRadius: 24, padding: 18, gap: 12 },
  summaryLabel: { color: colors.muted, marginBottom: 6 },
  summaryValue: { color: colors.text, fontSize: 22, fontWeight: '800' },

  // Playlist imported card
  importedCard: { backgroundColor: colors.cardAlt, borderRadius: 18, padding: 16, gap: 6 },
  importedName: { color: colors.text, fontSize: 18, fontWeight: '800' },

  // Stop Chrono
  chronoCard: { backgroundColor: colors.cardAlt, borderRadius: 20, padding: 18, gap: 12, alignItems: 'center' },
  chronoTarget: { color: colors.muted, fontWeight: '600' },
  chronoResult: { alignItems: 'center', gap: 8, alignSelf: 'stretch' },
  chronoResultTime: { color: colors.text, fontSize: 40, fontWeight: '900' },
  chronoResultDelta: { color: colors.accent, fontSize: 16, fontWeight: '700' },

  // Culture générale
  questionText: { color: colors.text, fontSize: 20, fontWeight: '800', lineHeight: 28 },
  answerCard: { backgroundColor: 'rgba(34,197,94,0.12)', borderRadius: 14, padding: 12, gap: 4, borderWidth: 1, borderColor: 'rgba(34,197,94,0.4)' },
  answerText: { color: '#bbf7d0', fontSize: 18, fontWeight: '800' },

  // Live / now playing
  liveCard: { backgroundColor: colors.cardAlt, borderRadius: 20, padding: 16, gap: 6 },
  nowPlayingLabel: { color: colors.muted, textTransform: 'uppercase', letterSpacing: 1.1, fontWeight: '700' },
  nowPlayingTitle: { color: colors.text, fontSize: 24, fontWeight: '800' },
  nowPlayingArtist: { color: colors.subtle, fontSize: 16, fontWeight: '600' },
  progressPill: { color: colors.accent, fontWeight: '800', fontSize: 18 },

  keyMapWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  keyChip: { backgroundColor: colors.cardAlt, borderRadius: 16, paddingHorizontal: 14, paddingVertical: 12, borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)', minWidth: 110 },
  keyChipLabel: { color: colors.muted, fontSize: 12, fontWeight: '700' },
  keyChipValue: { color: colors.text, marginTop: 6, fontSize: 18, fontWeight: '800', textTransform: 'uppercase' },

  scoreGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  scoreTile: { flexBasis: '48%', flexGrow: 1, backgroundColor: colors.cardAlt, borderRadius: 20, padding: 16, borderWidth: 1, borderColor: 'rgba(255,255,255,0.06)' },
  scoreTileActive: { borderColor: colors.accent, backgroundColor: 'rgba(34,197,94,0.16)' },
  scoreTileLabel: { color: colors.subtle, fontWeight: '700' },
  scoreTileValue: { color: colors.text, fontSize: 28, fontWeight: '800', marginTop: 10 },
  scoreTileHint: { color: colors.muted, marginTop: 6, fontSize: 12 },
  winnerText: { color: '#bbf7d0', fontWeight: '800', fontSize: 16, marginTop: 8 },

  // La Bombe
  bombeCard: { backgroundColor: '#241118', borderRadius: 24, padding: 20, gap: 14, borderWidth: 1, borderColor: 'rgba(239,68,68,0.45)', alignItems: 'center' },
  bombeLetter: { color: colors.text, fontSize: 88, lineHeight: 96, fontWeight: '900', textShadowColor: 'rgba(239,68,68,0.65)', textShadowRadius: 24 },
  bombeTeam: { color: '#fecaca', fontSize: 22, fontWeight: '900', textAlign: 'center' },
  bombeInstruction: { color: colors.muted, fontSize: 15, lineHeight: 22, textAlign: 'center' },

  // Mémoire en chaîne
  memoryFixedFooter: { flexShrink: 0, backgroundColor: '#102a3d', paddingHorizontal: 16, paddingTop: 12, paddingBottom: 14, gap: 10, borderTopWidth: 1, borderTopColor: '#38bdf8' },
  memoryActionLabel: { color: '#bae6fd', fontSize: 15, fontWeight: '800', textAlign: 'center' },
  memoryCard: { backgroundColor: '#111d2d', borderRadius: 24, padding: 20, gap: 14, borderWidth: 1, borderColor: 'rgba(56,189,248,0.42)' },
  memoryInstruction: { color: colors.muted, fontSize: 15, lineHeight: 22, textAlign: 'center' },
  memoryAnswerRow: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 14, backgroundColor: colors.cardAlt },
  memoryAnswerIndex: { width: 32, height: 32, borderRadius: 16, textAlign: 'center', textAlignVertical: 'center', color: '#082f49', backgroundColor: '#7dd3fc', fontWeight: '900' },
  memoryAnswerText: { flex: 1, color: colors.text, fontSize: 17, fontWeight: '800' },
  memoryWinner: { color: '#7dd3fc', fontSize: 30, fontWeight: '900', textAlign: 'center' },

  // Manche suivante / classement final
  mancheBanner: { backgroundColor: 'rgba(34,197,94,0.16)', borderRadius: 20, padding: 16, gap: 12, borderWidth: 1, borderColor: colors.accent },
  mancheBannerTitle: { color: colors.text, fontSize: 18, fontWeight: '800' },
  rankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 14,
    paddingHorizontal: 14,
    borderRadius: 14,
    backgroundColor: colors.cardAlt,
    borderWidth: 1,
    borderColor: colors.border,
  },
  rankRowWinner: { backgroundColor: 'rgba(34,197,94,0.2)', borderColor: colors.accent },
  rankPosition: { color: colors.accent, fontWeight: '900', fontSize: 20, width: 44 },
  rankTeam: { color: colors.text, fontWeight: '800', fontSize: 18, flex: 1 },
  rankScore: { color: colors.subtle, fontWeight: '700' },
});
