import { useKeepAwake } from 'expo-keep-awake';
import { Image, Pressable, StyleSheet, Text, View } from 'react-native';
import { useCountdown } from '../hooks/useCountdown';
import { useSendLock } from '../hooks/useSendLock';
import { useVolumeButtons } from '../hooks/useVolumeButtons';
import { mediaUrl } from '../services/backend';
import { colors, fonts, styles } from '../theme';
import { FairPriceState, GameConfigSnapshot, PriceItem } from '../types/gameConfig';

type Props = {
  snapshot: GameConfigSnapshot;
  errorMessage: string | null;
  onStartTurn: () => void;
  onHint: (direction: 'plus' | 'moins', proposals: number) => void;
  onFound: (proposals: number) => void;
  onBack: () => void;
};

const euros = (price: number): string => `${price.toLocaleString('fr-FR')} €`;
const seconds = (ms: number): string => `${(ms / 1000).toFixed(1).replace('.', ',')} s`;

const headline = (game: FairPriceState): string => {
  if (game.phase === 'running') return `${game.current_team} cherche le prix`;
  if (game.phase === 'ready') return `Au tour de ${game.current_team}`;
  if (game.phase === 'finished') return game.winner_team === 'Égalité' ? 'Personne n’a trouvé' : `${game.winner_team} remporte la manche`;
  return 'Le juste prix';
};

export function FairPriceLiveScreen({ snapshot, errorMessage, onStartTurn, onHint, onFound, onBack }: Props) {
  const game = snapshot.session.fair_price;
  const running = game.phase === 'running';
  const item = game.current_item;
  // Un appui par proposition : le serveur ignore de toute façon une décision rejouée (même `proposals`).
  const [deciding, decideOnce] = useSendLock(`${game.results.length}-${game.proposals}`);
  const [starting, startOnce] = useSendLock(`start-${game.results.length}`);

  const hint = (direction: 'plus' | 'moins') => decideOnce(() => onHint(direction, game.proposals));
  const volumeButtonsActive = useVolumeButtons({ enabled: running, onVolumeUp: () => hint('plus'), onVolumeDown: () => hint('moins') });

  return (
    <>
      <Pressable style={styles.backButton} onPress={onBack}>
        <Text style={styles.backButtonText}>‹ Reconfigurer</Text>
      </Pressable>

      <View style={styles.heroCard}>
        <Text style={styles.eyebrow}>Le juste prix · {game.band_label}</Text>
        <Text style={styles.title}>{headline(game)}</Text>
        {game.phase !== 'finished' && game.turn_order.length ? (
          <Text style={styles.subtitle}>
            Équipe {Math.min(game.results.length + 1, game.turn_order.length)}/{game.turn_order.length} · le plus rapide gagne
          </Text>
        ) : null}
        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </View>

      {item && (running || game.phase === 'ready') ? <ItemCard item={item} /> : null}

      {game.phase === 'ready' ? (
        <View style={styles.sectionCard}>
          <Text style={styles.helperText}>
            L’objet n’apparaît à l’écran qu’au lancement du chrono. Répondez « plus » ou « moins » à chaque prix annoncé.
          </Text>
          <Pressable
            style={[styles.primaryButton, starting && styles.primaryButtonDisabled]}
            onPress={() => startOnce(onStartTurn)}
            disabled={starting}
            accessibilityRole="button"
          >
            <Text style={styles.primaryButtonText}>Lancer le chrono · {Math.round(game.turn_ms / 1000)} s</Text>
          </Pressable>
        </View>
      ) : null}

      {running ? (
        <View style={styles.sectionCard}>
          <TurnClock deadlineMs={game.deadline_ms} turnMs={game.turn_ms} proposals={game.proposals} />
          <View style={local.hintRow}>
            <HintButton label="C’est plus" arrow="▲" color={colors.blue} disabled={deciding} onPress={() => hint('plus')} />
            <HintButton label="C’est moins" arrow="▼" color={colors.pink} disabled={deciding} onPress={() => hint('moins')} />
          </View>
          <Pressable
            style={[styles.primaryButton, styles.successButton, deciding && styles.primaryButtonDisabled]}
            onPress={() => decideOnce(() => onFound(game.proposals))}
            disabled={deciding}
            accessibilityRole="button"
          >
            <Text style={[styles.primaryButtonText, local.foundText]}>Trouvé !</Text>
          </Pressable>
          <Text style={styles.helperText}>
            {volumeButtonsActive ? 'Volume + : c’est plus · Volume − : c’est moins' : 'Boutons volume inactifs (uniquement en APK).'}
          </Text>
        </View>
      ) : null}

      <View style={styles.sectionCard}>
        <Text style={styles.sectionTitle}>Chronos</Text>
        {game.turn_order.map((team, index) => {
          const result = game.results[index];
          return (
            <View key={team} style={[styles.rankRow, team === game.current_team && styles.rankRowWinner, team === game.winner_team && styles.rankRowWinner]}>
              <Text style={styles.rankPosition}>{index + 1}</Text>
              <View style={local.resultTeam}>
                <Text style={styles.rankTeam} numberOfLines={1}>{team}</Text>
                {result ? <Text style={local.resultItem}>{result.item.name} · {euros(result.item.price)}</Text> : null}
              </View>
              <Text style={local.resultTime}>{result ? (result.found ? seconds(result.elapsed_ms) : '—') : ''}</Text>
            </View>
          );
        })}
      </View>
    </>
  );
}

function ItemCard({ item }: { item: PriceItem }) {
  const url = mediaUrl('fair-price', item.image);
  return (
    <View style={local.itemCard}>
      {url ? <Image source={{ uri: url }} style={local.itemImage} resizeMode="contain" accessibilityLabel={item.name} /> : null}
      <View style={local.itemInfo}>
        <Text style={local.itemName}>{item.name}</Text>
        <Text style={local.priceLabel}>Vrai prix · régie uniquement</Text>
        <Text style={local.price}>{euros(item.price)}</Text>
      </View>
    </View>
  );
}

type HintButtonProps = { label: string; arrow: string; color: string; disabled: boolean; onPress: () => void };

function HintButton({ label, arrow, color, disabled, onPress }: HintButtonProps) {
  return (
    <Pressable
      style={[local.hintButton, { backgroundColor: color }, disabled && styles.primaryButtonDisabled]}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Text style={local.hintArrow}>{arrow}</Text>
      <Text style={local.hintText}>{label}</Text>
    </Pressable>
  );
}

// Isolé pour que seul le chrono se re-rende ; l'écran reste allumé pendant le tour.
function TurnClock({ deadlineMs, turnMs, proposals }: { deadlineMs: number; turnMs: number; proposals: number }) {
  useKeepAwake();
  const remainingMs = useCountdown(deadlineMs, true, 100);
  return (
    <View style={local.clockRow} accessibilityRole="timer">
      <Text style={local.clock}>{seconds(turnMs - remainingMs)}</Text>
      <Text style={local.proposals}>
        {proposals} proposition{proposals > 1 ? 's' : ''} · {Math.ceil(remainingMs / 1000)} s restantes
      </Text>
    </View>
  );
}

const local = StyleSheet.create({
  itemCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    padding: 16,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: colors.gold,
    backgroundColor: colors.card,
  },
  itemImage: { width: 120, height: 90, borderRadius: 10, backgroundColor: colors.bg },
  itemInfo: { flex: 1, gap: 2 },
  itemName: { color: colors.text, fontFamily: fonts.display, fontSize: 22, textTransform: 'uppercase' },
  priceLabel: { color: colors.muted, fontFamily: fonts.bold, fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.6 },
  price: { color: colors.gold, fontFamily: fonts.display, fontSize: 40, lineHeight: 46 },
  clockRow: { alignItems: 'center', gap: 2 },
  clock: { color: colors.gold, fontFamily: fonts.display, fontSize: 44, fontVariant: ['tabular-nums'] },
  proposals: { color: colors.muted, fontFamily: fonts.bold },
  hintRow: { flexDirection: 'row', gap: 12 },
  hintButton: { flex: 1, alignItems: 'center', paddingVertical: 18, borderRadius: 12, borderBottomWidth: 5, borderBottomColor: 'rgba(0,0,0,0.35)' },
  hintArrow: { color: '#fff', fontSize: 22 },
  hintText: { color: '#fff', fontFamily: fonts.display, fontSize: 20, textTransform: 'uppercase' },
  foundText: { color: colors.ink, fontSize: 22 },
  resultTeam: { flex: 1, gap: 2 },
  resultItem: { color: colors.muted, fontFamily: fonts.regular, fontSize: 13 },
  resultTime: { color: colors.gold, fontFamily: fonts.display, fontSize: 20, fontVariant: ['tabular-nums'] },
});
