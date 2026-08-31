import { useEffect, useState } from 'react';
import { Pressable, SafeAreaView, ScrollView, StatusBar, Text, View } from 'react-native';
import { StatusBar as ExpoStatusBar } from 'expo-status-bar';
import { GameConfigControllerSocket } from './src/services/realtime/gameConfigControllerSocket';
import { useGameConfigStore } from './src/store/gameConfigStore';
import { ConfigScreen } from './src/screens/ConfigScreen';
import { PlaylistSetupScreen } from './src/screens/PlaylistSetupScreen';
import { LiveScreen } from './src/screens/LiveScreen';
import { StopChronoLiveScreen } from './src/screens/StopChronoLiveScreen';
import { CultureLiveScreen } from './src/screens/CultureLiveScreen';
import { BombeLiveScreen } from './src/screens/BombeLiveScreen';
import { FinalRankingScreen } from './src/screens/FinalRankingScreen';
import { styles } from './src/theme';

const socket = new GameConfigControllerSocket();

type Step = 'config' | 'playlist' | 'live';

export default function App() {
  const { draft, remoteSnapshot, connectionState, errorMessage, setDraft, setRemoteSnapshot, setConnectionState, setErrorMessage } =
    useGameConfigStore();
  // On démarre toujours sur l'écran de configuration.
  const [step, setStep] = useState<Step>('config');

  useEffect(() => {
    socket.connect({
      onSnapshot: setRemoteSnapshot,
      onStatusChange: setConnectionState,
      onError: setErrorMessage,
    });
    return () => socket.disconnect();
  }, [setConnectionState, setErrorMessage, setRemoteSnapshot]);

  const validateConfig = () => {
    socket.replaceConfig({ ...draft, status: 'ready' });
    socket.launchGame();
    setStep('playlist');
  };

  const session = remoteSnapshot?.session;
  const activeGameKey = session?.active_round?.game_key;
  const partyFinished = remoteSnapshot?.status === 'finished';
  const mancheFinished = Boolean(session?.manche_finished) && !partyFinished;

  return (
    <SafeAreaView style={styles.safeArea}>
      <ExpoStatusBar style="light" />
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.container}>
        {step === 'config' ? (
          <ConfigScreen
            draft={draft}
            setDraft={setDraft}
            connectionState={connectionState}
            errorMessage={errorMessage}
            onValidate={validateConfig}
          />
        ) : null}

        {step === 'playlist' ? (
          <PlaylistSetupScreen
            snapshot={remoteSnapshot}
            connectionState={connectionState}
            errorMessage={errorMessage}
            onReloadPlaylist={() => socket.reloadPlaylist()}
            onContinue={() => setStep('live')}
            onBack={() => setStep('config')}
          />
        ) : null}

        {step === 'live' && remoteSnapshot && partyFinished ? (
          <FinalRankingScreen
            snapshot={remoteSnapshot}
            onRevealNext={() => socket.revealNextRanking()}
            onBack={() => setStep('config')}
          />
        ) : null}

        {step === 'live' && remoteSnapshot && !partyFinished ? (
          <>
            {mancheFinished ? (
              <View style={styles.mancheBanner}>
                <Text style={styles.mancheBannerTitle}>
                  {session?.manche_winner && session.manche_winner !== 'Égalité'
                    ? `Manche remportée par ${session.manche_winner}`
                    : 'Manche terminée — égalité'}
                </Text>
                <Pressable style={styles.primaryButton} onPress={() => socket.nextManche()}>
                  <Text style={styles.primaryButtonText}>
                    {session && session.manche_number >= session.total_rounds ? 'Voir le classement final' : 'Manche suivante'}
                  </Text>
                </Pressable>
              </View>
            ) : null}

            {activeGameKey === 'bombe' ? (
              <BombeLiveScreen
                snapshot={remoteSnapshot}
                errorMessage={errorMessage}
                onStart={() => socket.startBombe()}
                onBuzz={(team) => socket.bombeBuzzer(team)}
                onPreviousTeam={() => socket.previousBombeTeam()}
                onBack={() => setStep('config')}
              />
            ) : activeGameKey === 'stopchrono' ? (
              <StopChronoLiveScreen
                snapshot={remoteSnapshot}
                errorMessage={errorMessage}
                onStart={() => socket.startChrono()}
                onStop={() => socket.stopChrono()}
                onNext={() => socket.nextChronoTeam()}
                onBack={() => setStep('config')}
              />
            ) : activeGameKey === 'culture' ? (
              <CultureLiveScreen
                snapshot={remoteSnapshot}
                errorMessage={errorMessage}
                onStart={() => socket.startCulture()}
                onSelectDifficulty={(difficulty) => socket.selectCultureDifficulty(difficulty)}
                onBuzz={(team) => socket.cultureBuzzer(team)}
                onAnswer={(isCorrect) => socket.cultureAnswer(isCorrect)}
                onNext={() => socket.nextCultureQuestion()}
                onBack={() => setStep('config')}
              />
            ) : (
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
            )}
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}
