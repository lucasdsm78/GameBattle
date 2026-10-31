import { StyleSheet } from 'react-native';

// Habillage « plateau TV », identique à l'écran public : titres en Anton, texte en Barlow Semi Condensed.
export const colors = {
  bg: '#0b0721',
  card: '#1a1145',
  cardAlt: '#241760',
  hero: '#1d1252',
  input: '#130b36',
  edge: '#4330a6',
  text: '#ffffff',
  muted: '#bfb6ee',
  subtle: '#ddd6ff',
  ink: '#170c39',
  gold: '#ffc629',
  goldDeep: '#c98a00',
  pink: '#ff2e88',
  pinkDeep: '#9c0a52',
  accent: '#22dd6b', // juste / positif
  accentDark: '#139a48',
  danger: '#ff3d5e', // faux / négatif
  dangerDeep: '#a3122f',
  border: 'rgba(255,255,255,0.14)',
};

// Familles chargées par App.tsx (useFonts). Avec une police embarquée, on choisit la famille plutôt que fontWeight.
export const fonts = {
  display: 'Anton_400Regular',
  regular: 'BarlowSemiCondensed_600SemiBold',
  bold: 'BarlowSemiCondensed_700Bold',
  black: 'BarlowSemiCondensed_800ExtraBold',
};

// Bouton de plateau : aplat franc et tranche plus sombre en bas, comme un buzzer.
const gameButton = { borderRadius: 12, borderBottomWidth: 5, alignItems: 'center' as const };

export const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.bg },
  scrollView: { flex: 1 },
  container: { padding: 16, gap: 16, backgroundColor: colors.bg, paddingBottom: 48 },

  // Stepper
  stepper: { flexDirection: 'row', gap: 8, marginBottom: 4 },
  stepPill: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: 'rgba(255,255,255,0.06)',
    alignItems: 'center',
    transform: [{ skewX: '-10deg' }],
  },
  stepPillActive: { backgroundColor: colors.gold },
  stepPillDone: { backgroundColor: 'rgba(255,198,41,0.25)' },
  stepPillText: { color: colors.subtle, fontFamily: fonts.display, fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.6 },
  stepPillTextActive: { color: colors.ink },

  // Hero / headers
  heroCard: {
    backgroundColor: colors.hero,
    borderRadius: 14,
    padding: 18,
    borderWidth: 2,
    borderColor: colors.edge,
    borderLeftWidth: 6,
    borderLeftColor: colors.pink,
  },
  eyebrow: { color: colors.gold, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, fontFamily: fonts.display, fontSize: 15 },
  title: { color: colors.text, fontSize: 28, lineHeight: 32, fontFamily: fonts.display, textTransform: 'uppercase' },
  subtitle: { color: colors.muted, marginTop: 8, lineHeight: 22, fontFamily: fonts.regular, fontSize: 15 },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16 },
  badge: { backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: 6, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 12, paddingVertical: 7 },
  badgeSuccess: { backgroundColor: 'rgba(34,221,107,0.2)', borderColor: colors.accent },
  badgeWarning: { backgroundColor: 'rgba(255,198,41,0.2)', borderColor: colors.gold },
  badgeText: { color: colors.text, textTransform: 'uppercase', fontFamily: fonts.black, fontSize: 12, letterSpacing: 0.8 },
  helperText: { color: colors.muted, marginTop: 12, fontFamily: fonts.regular, fontSize: 14, lineHeight: 20 },
  errorText: { color: '#ffb3c1', marginTop: 12, fontFamily: fonts.bold },

  // Sections / cards
  sectionCard: { backgroundColor: colors.card, borderRadius: 14, padding: 16, borderWidth: 2, borderColor: colors.edge, gap: 12 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  sectionTitle: { color: colors.text, fontSize: 22, fontFamily: fonts.display, textTransform: 'uppercase' },
  roundCard: { backgroundColor: colors.cardAlt, borderRadius: 12, padding: 14, gap: 12 },
  roundTitle: { color: colors.text, fontSize: 17, fontFamily: fonts.bold },

  // Fields
  fieldWrap: { gap: 8, flex: 1 },
  inputLabel: { color: colors.subtle, fontFamily: fonts.bold },
  input: {
    backgroundColor: colors.input,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.edge,
    color: colors.text,
    fontFamily: fonts.bold,
    fontSize: 16,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },

  // Buttons
  primaryButton: { ...gameButton, backgroundColor: colors.gold, borderBottomColor: colors.goldDeep, paddingVertical: 15 },
  primaryButtonCompact: {
    ...gameButton,
    backgroundColor: colors.gold,
    borderBottomColor: colors.goldDeep,
    paddingVertical: 13,
    paddingHorizontal: 18,
    flexGrow: 1,
  },
  primaryButtonText: { color: colors.ink, fontFamily: fonts.display, fontSize: 18, textTransform: 'uppercase', letterSpacing: 0.4 },
  primaryButtonDisabled: { opacity: 0.4 },
  secondaryButton: { backgroundColor: 'rgba(255,198,41,0.16)', paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: colors.gold },
  secondaryButtonText: { color: colors.gold, fontFamily: fonts.black },
  ghostButton: {
    backgroundColor: 'rgba(255,255,255,0.06)',
    paddingHorizontal: 14,
    paddingVertical: 11,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.border,
    alignItems: 'center',
  },
  ghostButtonText: { color: colors.text, fontFamily: fonts.bold },
  backButton: { alignSelf: 'flex-start', paddingVertical: 8, paddingHorizontal: 4 },
  backButtonText: { color: colors.muted, fontFamily: fonts.bold },
  successButton: { backgroundColor: colors.accent, borderBottomColor: colors.accentDark },
  falseButton: { backgroundColor: colors.danger, borderBottomColor: colors.dangerDeep },

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
    borderRadius: 10,
    alignItems: 'center',
    backgroundColor: colors.cardAlt,
    borderWidth: 2,
    borderColor: colors.edge,
  },
  difficultyChip: {
    flexGrow: 1,
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderRadius: 10,
    alignItems: 'center',
    backgroundColor: colors.cardAlt,
    borderWidth: 2,
    borderColor: colors.edge,
  },
  gameChipActive: { backgroundColor: colors.gold, borderColor: colors.goldDeep },
  gameChipText: { color: colors.subtle, fontFamily: fonts.black },
  gameChipTextActive: { color: colors.ink },

  // Teams
  teamRow: { gap: 10 },
  removeText: { color: '#ffb3c1', fontFamily: fonts.bold },
  removeTextDisabled: { opacity: 0.35 },

  // Summary
  summaryCard: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: colors.hero, borderRadius: 14, padding: 18, gap: 12, borderWidth: 2, borderColor: colors.edge },
  summaryLabel: { color: colors.muted, marginBottom: 6, fontFamily: fonts.regular },
  summaryValue: { color: colors.gold, fontSize: 26, fontFamily: fonts.display },

  // Playlist imported card
  importedCard: { backgroundColor: colors.cardAlt, borderRadius: 12, padding: 16, gap: 6 },
  importedName: { color: colors.text, fontSize: 18, fontFamily: fonts.black },

  // Stop Chrono
  chronoCard: { backgroundColor: colors.cardAlt, borderRadius: 14, padding: 18, gap: 12, alignItems: 'center', borderWidth: 2, borderColor: colors.edge },
  chronoTarget: { color: colors.muted, fontFamily: fonts.bold },
  chronoResult: { alignItems: 'center', gap: 8, alignSelf: 'stretch' },
  chronoResultTime: { color: colors.text, fontSize: 44, fontFamily: fonts.display },
  chronoResultDelta: { color: colors.gold, fontSize: 16, fontFamily: fonts.black },

  // Culture générale
  questionText: { color: colors.text, fontSize: 21, fontFamily: fonts.black, lineHeight: 28 },
  answerCard: { backgroundColor: 'rgba(34,221,107,0.12)', borderRadius: 10, padding: 12, gap: 4, borderWidth: 2, borderColor: 'rgba(34,221,107,0.45)' },
  answerText: { color: '#b6ffd2', fontSize: 19, fontFamily: fonts.black },

  // Live / now playing
  liveCard: { backgroundColor: colors.cardAlt, borderRadius: 14, padding: 16, gap: 6, borderWidth: 2, borderColor: colors.edge },
  nowPlayingLabel: { color: colors.muted, textTransform: 'uppercase', letterSpacing: 1, fontFamily: fonts.black, fontSize: 12 },
  nowPlayingTitle: { color: colors.text, fontSize: 26, fontFamily: fonts.display, textTransform: 'uppercase' },
  nowPlayingArtist: { color: colors.gold, fontSize: 16, fontFamily: fonts.bold },
  progressPill: { color: colors.gold, fontFamily: fonts.display, fontSize: 20 },

  keyMapWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  keyChip: { backgroundColor: colors.cardAlt, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12, borderWidth: 2, borderColor: colors.edge, minWidth: 110 },
  keyChipLabel: { color: colors.muted, fontSize: 12, fontFamily: fonts.bold },
  keyChipValue: { color: colors.gold, marginTop: 6, fontSize: 20, fontFamily: fonts.display, textTransform: 'uppercase' },

  scoreGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  scoreTile: {
    flexBasis: '48%',
    flexGrow: 1,
    backgroundColor: colors.cardAlt,
    borderRadius: 12,
    padding: 14,
    borderWidth: 2,
    borderColor: colors.edge,
    borderBottomWidth: 5,
  },
  scoreTileActive: { borderColor: colors.gold, backgroundColor: 'rgba(255,198,41,0.16)' },
  scoreTileLabel: { color: colors.subtle, fontFamily: fonts.black, fontSize: 15 },
  scoreTileValue: { color: colors.text, fontSize: 30, fontFamily: fonts.display, marginTop: 8 },
  scoreTileHint: { color: colors.muted, marginTop: 6, fontSize: 12, fontFamily: fonts.regular },
  winnerText: { color: colors.gold, fontFamily: fonts.display, fontSize: 18, marginTop: 8, textTransform: 'uppercase' },

  // La Bombe
  bombeCard: { backgroundColor: '#241032', borderRadius: 14, padding: 20, gap: 14, borderWidth: 2, borderColor: 'rgba(255,61,94,0.55)', alignItems: 'center' },
  bombeLetter: { color: colors.text, fontSize: 84, lineHeight: 96, fontFamily: fonts.display, textShadowColor: 'rgba(255,61,94,0.7)', textShadowRadius: 24 },
  bombeTeam: { color: '#ffc2cd', fontSize: 24, fontFamily: fonts.display, textAlign: 'center', textTransform: 'uppercase' },
  bombeInstruction: { color: colors.muted, fontSize: 15, lineHeight: 22, textAlign: 'center', fontFamily: fonts.regular },

  // Mémoire en chaîne
  memoryFixedFooter: { flexShrink: 0, backgroundColor: colors.hero, paddingHorizontal: 16, paddingTop: 12, paddingBottom: 14, gap: 10, borderTopWidth: 3, borderTopColor: colors.gold },
  memoryActionLabel: { color: colors.gold, fontSize: 16, fontFamily: fonts.display, textAlign: 'center', textTransform: 'uppercase' },
  memoryCard: { backgroundColor: colors.card, borderRadius: 14, padding: 20, gap: 14, borderWidth: 2, borderColor: colors.edge },
  memoryInstruction: { color: colors.muted, fontSize: 15, lineHeight: 22, textAlign: 'center', fontFamily: fonts.regular },
  memoryAnswerRow: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 10, backgroundColor: colors.cardAlt },
  memoryAnswerIndex: {
    width: 32,
    height: 32,
    borderRadius: 16,
    overflow: 'hidden',
    textAlign: 'center',
    textAlignVertical: 'center',
    lineHeight: 32,
    color: colors.ink,
    backgroundColor: colors.gold,
    fontFamily: fonts.display,
  },
  memoryAnswerText: { flex: 1, color: colors.text, fontSize: 17, fontFamily: fonts.black },
  memoryWinner: { color: colors.gold, fontSize: 32, fontFamily: fonts.display, textAlign: 'center', textTransform: 'uppercase' },

  // Manche suivante / classement final
  mancheBanner: { backgroundColor: 'rgba(255,198,41,0.14)', borderRadius: 14, padding: 16, gap: 12, borderWidth: 2, borderColor: colors.gold },
  mancheBannerTitle: { color: colors.text, fontSize: 22, fontFamily: fonts.display, textTransform: 'uppercase' },
  rankRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 10,
    backgroundColor: colors.cardAlt,
    borderWidth: 2,
    borderColor: colors.border,
  },
  rankRowWinner: { backgroundColor: 'rgba(255,198,41,0.16)', borderColor: colors.gold },
  rankPosition: { color: colors.gold, fontFamily: fonts.display, fontSize: 22, width: 44 },
  rankTeam: { color: colors.text, fontFamily: fonts.black, fontSize: 18, flex: 1 },
  rankScore: { color: colors.subtle, fontFamily: fonts.bold },
});
