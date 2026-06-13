import { create } from 'zustand';
import { GameConfigSnapshot } from '../types/gameConfig';

type GameDraft = Pick<GameConfigSnapshot, 'settings' | 'games' | 'rounds' | 'status'>;

const defaultDraft: GameDraft = {
  settings: {
    game_title: 'GameBattle Night',
    random_round_order: true,
    teams: ['Équipe Rouge', 'Équipe Bleue'],
    buzzer_keys: ['1', '2'],
    total_rounds: 4,
    culture_difficulty: 'toutes',
  },
  games: [
    { game_key: 'blindtest', label: 'Blindtest', enabled: true, round_count: 0 },
    { game_key: 'stopchrono', label: 'Stop Chrono', enabled: false, round_count: 0 },
    { game_key: 'culture', label: 'Culture générale', enabled: false, round_count: 0 },
  ],
  rounds: [],
  status: 'configuring',
};

type State = {
  draft: GameDraft;
  remoteSnapshot: GameConfigSnapshot | null;
  connectionState: 'connecting' | 'connected' | 'disconnected';
  errorMessage: string | null;
  setDraft: (draft: GameDraft) => void;
  setRemoteSnapshot: (snapshot: GameConfigSnapshot) => void;
  setConnectionState: (state: State['connectionState']) => void;
  setErrorMessage: (message: string | null) => void;
};

export const useGameConfigStore = create<State>((set) => ({
  draft: defaultDraft,
  remoteSnapshot: null,
  connectionState: 'connecting',
  errorMessage: null,
  setDraft: (draft) => set({ draft }),
  setRemoteSnapshot: (remoteSnapshot) =>
    set({
      remoteSnapshot,
      draft: {
        settings: remoteSnapshot.settings,
        games: remoteSnapshot.games,
        rounds: remoteSnapshot.rounds,
        status: remoteSnapshot.status,
      },
      errorMessage: null,
    }),
  setConnectionState: (connectionState) => set({ connectionState }),
  setErrorMessage: (errorMessage) => set({ errorMessage }),
}));

