import { create } from 'zustand';
import { GameConfigSnapshot } from '../types/gameConfig';

type State = {
  gameConfig: GameConfigSnapshot | null;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  setGameConfig: (config: GameConfigSnapshot) => void;
  setConnectionState: (state: State['connectionState']) => void;
  setErrorMessage: (message: string | null) => void;
};

export const useGameConfigStore = create<State>((set) => ({
  gameConfig: null,
  connectionState: 'connecting',
  errorMessage: null,
  setGameConfig: (gameConfig) => set({ gameConfig, errorMessage: null }),
  setConnectionState: (connectionState) => set({ connectionState }),
  setErrorMessage: (errorMessage) => set({ errorMessage }),
}));
