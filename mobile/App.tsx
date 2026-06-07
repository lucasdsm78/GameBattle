import { useEffect, useState } from 'react';
import { SafeAreaView, ScrollView, StatusBar, Text, View } from 'react-native';
import { StatusBar as ExpoStatusBar } from 'expo-status-bar';
import { GameConfigControllerSocket } from './src/services/realtime/gameConfigControllerSocket';
import { useGameConfigStore } from './src/store/gameConfigStore';
import { ConfigScreen } from './src/screens/ConfigScreen';
import { LiveScreen } from './src/screens/LiveScreen';
import { styles } from './src/theme';

const socket = new GameConfigControllerSocket();

type Step = 'config' | 'live';
const STEP_LABELS: { key: Step; label: string }[] = [
  { key: 'config', label: 'Partie' },
  { key: 'live', label: 'Blindtest' },
];
const STEP_ORDER: Step[] = ['config', 'live'];

export default function App() {
  const { draft, remoteSnapshot, connectionState, errorMessage, setDraft, setRemoteSnapshot, setConnectionState, setErrorMessage } =
    useGameConfigStore();
  // On démarre toujours sur l'écran de configuration, même si une partie est encore persistée en base.
  const [step, setStep] = useState<Step>('config');

  useEffect(() => {
    socket.connect({
      onSnapshot: setRemoteSnapshot,
      onStatusChange: setConnectionState,
      onError: setErrorMessage,
    });
    return () => socket.disconnect();
  }, [setConnectionState, setErrorMessage, setRemoteSnapshot]);

  // Valider la config lance la partie : le backend importe automatiquement la playlist fixe
  // (GAMEBATTLE_BLINDTEST_PLAYLIST_URL) puis on passe directement au blindtest en direct.
  const validateConfig = () => {
    socket.replaceConfig({ ...draft, status: 'ready' });
    socket.launchGame();
    setStep('live');
  };

  const currentIndex = STEP_ORDER.indexOf(step);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ExpoStatusBar style="light" />
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.stepper}>
          {STEP_LABELS.map((entry, index) => {
            const active = entry.key === step;
            const done = index < currentIndex;
            return (
              <View
                key={entry.key}
                style={[styles.stepPill, active && styles.stepPillActive, done && styles.stepPillDone]}
              >
                <Text style={[styles.stepPillText, active && styles.stepPillTextActive]}>{entry.label}</Text>
              </View>
            );
          })}
        </View>

        {step === 'config' ? (
          <ConfigScreen
            draft={draft}
            setDraft={setDraft}
            connectionState={connectionState}
            errorMessage={errorMessage}
            onValidate={validateConfig}
          />
        ) : null}

        {step === 'live' && remoteSnapshot ? (
          <LiveScreen
            snapshot={remoteSnapshot}
            errorMessage={errorMessage}
            onPlay={() => socket.controlPlayback('play')}
            onPause={() => socket.controlPlayback('pause')}
            onBuzz={(team) => socket.buzz(team)}
            onAnswer={(isCorrect) => socket.answer(isCorrect)}
            onNext={() => socket.nextTrack()}
            onReloadPlaylist={() => socket.reloadPlaylist()}
            onBack={() => setStep('config')}
          />
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
