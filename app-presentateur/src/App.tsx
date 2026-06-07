import { useEffect } from 'react';
import { DisplayBoard } from './components/DisplayBoard';
import { GameConfigSocket } from './services/realtime/gameConfigSocket';
import { useGameConfigStore } from './store/gameConfigStore';

const socket = new GameConfigSocket();

export default function App() {
  const { gameConfig, connectionState, errorMessage, setConnectionState, setErrorMessage, setGameConfig } =
    useGameConfigStore();

  useEffect(() => {
    socket.connect({
      onStatusChange: setConnectionState,
      onError: setErrorMessage,
      onMessage: (message) => {
        if (message.payload) {
          setGameConfig(message.payload);
        }
        if (message.type === 'error' && message.detail) {
          setErrorMessage(message.detail);
        }
      },
    });

    return () => socket.disconnect();
  }, [setConnectionState, setErrorMessage, setGameConfig]);

  return (
    <DisplayBoard
      gameConfig={gameConfig}
      connectionState={connectionState}
      errorMessage={errorMessage}
      onBuzz={(team) => socket.buzz(team)}
    />
  );
}
