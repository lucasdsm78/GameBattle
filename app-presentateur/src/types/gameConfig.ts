export type GameKey = 'blindtest' | 'stopchrono';

export type GameStatus = 'configuring' | 'ready' | 'live' | 'finished';

export type GameSettings = {
  game_title: string;
  random_round_order: boolean;
  teams: string[];
  buzzer_keys: string[];
  total_rounds: number;
};

export type RankingEntry = {
  team: string;
  manches_won: number;
  rank: number;
};

export type GameDefinition = {
  game_key: GameKey;
  label: string;
  enabled: boolean;
  round_count: number;
};

export type GameRoundPlan = {
  id: string;
  label: string;
  game_key: GameKey;
  planned_track_count: number;
  buzzer_enabled: boolean;
};

export type BlindtestTrack = {
  track_id: string;
  title: string;
  artist: string;
  preview_url: string;
  artwork_url: string;
};

export type ActiveRound = {
  round_id: string;
  label: string;
  game_key: GameKey;
  order_index: number;
  completed: boolean;
};

export type BlindtestState = {
  round_id: string;
  total_tracks: number;
  current_track_index: number;
  current_track: BlindtestTrack | null;
  current_buzzer_team: string | null;
  revealed: boolean;
  playback_state: 'stopped' | 'playing' | 'paused';
  scores: Record<string, number>;
  winner_team: string | null;
  tracks: BlindtestTrack[];
  tracks_remaining: number;
  playlist_name: string;
  playlist_source_url: string;
  playlist_provider: string;
  playback_position_ms: number;
  playback_duration_ms: number;
  playback_updated_at: string;
};

export type StopChronoState = {
  target_ms: number;
  target_seconds: number;
  phase: 'idle' | 'running' | 'revealed' | 'finished';
  current_team_index: number;
  current_team: string | null;
  started_at_ms: number;
  results: Record<string, number>;
  deltas_ms: Record<string, number>;
  scores: Record<string, number>;
  winner_team: string | null;
};

export type GameSession = {
  active_round: ActiveRound | null;
  blindtest: BlindtestState;
  stopchrono: StopChronoState;
  round_index: number;
  total_rounds: number;
  manche_number: number;
  manches_won: Record<string, number>;
  manche_finished: boolean;
  manche_winner: string | null;
  final_ranking: RankingEntry[];
  final_ranking_total: number;
  ranking_reveal_count: number;
  updated_at: string;
};

export type GameConfigSnapshot = {
  settings: GameSettings;
  games: GameDefinition[];
  rounds: GameRoundPlan[];
  session: GameSession;
  status: GameStatus;
  updated_at: string;
  summary: {
    round_count: number;
    enabled_game_count: number;
    teams: number;
  };
};

export type GameConfigMessage = {
  type: 'game.config.snapshot' | 'game.config.updated' | 'error' | 'pong';
  payload?: GameConfigSnapshot;
  detail?: string;
};

