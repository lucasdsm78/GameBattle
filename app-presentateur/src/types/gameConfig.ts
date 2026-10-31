export type GameKey =
  | 'blindtest'
  | 'stopchrono'
  | 'culture'
  | 'bombe'
  | 'memory'
  | 'seven_differences'
  | 'auction'
  | 'forbidden_word'
  | 'vanishing_word'
  | 'flash_calc'
  | 'right_flag'
  | 'golden_family';

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

export type CultureQuestion = {
  id: string;
  question: string;
  answer: string;
  explanation: string;
  difficulty: string;
};

export type CultureState = {
  phase: 'idle' | 'selecting' | 'question' | 'finished';
  current_index: number;
  total_questions: number;
  questions_remaining: number;
  difficulty: string;
  current_buzzer_team: string | null;
  answered: boolean;
  scores: Record<string, number>;
  // Non vide pendant la question de départage : seules ces équipes peuvent buzzer.
  tiebreak_teams: string[];
  winner_team: string | null;
  current_question: CultureQuestion | null;
};

export type BombeState = {
  phase: 'idle' | 'awaiting_roll' | 'rolling' | 'running' | 'exploded';
  letter: string;
  current_team_index: number;
  turn_history: number[];
  started_at_ms: number;
  deadline_at_ms: number;
  exploded_team: string | null;
  winner_team: string | null;
  scores: Record<string, number>;
  eligible_team_indices: number[];
  tiebreak_round: number;
  sound: string;
  die_result: 'TIC' | 'TAC' | 'BOUM' | '';
  roller_team_index: number | null;
  die_reveal_at_ms: number;
};

export type MemoryState = {
  phase: 'idle' | 'question' | 'recitation' | 'finished';
  current_team_index: number;
  qualified_team_indices: number[];
  disqualified_teams: string[];
  current_question: CultureQuestion | null;
  validated_answers: string[];
  asked_questions: string[];
  sequence_length: number;
  chain_length: number;
  turn_number: number;
  winner_team: string | null;
  rules_version: number;
};

export type SevenDifference = {
  id: string;
  label: string;
};

export type SevenDifferencesState = {
  phase: 'idle' | 'memorizing' | 'open' | 'claimed' | 'finished';
  puzzle_id: string;
  title: string;
  original_image_url: string;
  modified_image_url: string;
  differences: SevenDifference[];
  found_difference_ids: string[];
  differences_remaining: number;
  reveal_at_ms: number;
  current_buzzer_team: string | null;
  blocked_team: string | null;
  scores: Record<string, number>;
  winner_team: string | null;
};

export type AuctionState = {
  phase: 'idle' | 'bidding' | 'ready' | 'running' | 'resolved' | 'finished';
  theme_id: string;
  prompt: string;
  answers: string[];
  bidding_teams: string[];
  active_team: string | null;
  target_count: number;
  correct_count: number;
  started_at_ms: number;
  deadline_at_ms: number;
  scores: Record<string, number>;
  attempt_succeeded: boolean | null;
  points_awarded: Record<string, number>;
  winner_team: string | null;
};

export type ForbiddenWordTurn = {
  team: string;
  found_words: string[];
  skipped_words: string[];
  round: number; // 0 : la manche ; 1, 2… : les tours de mort subite
};

// Tant que le mot n'est pas révélé, `words` est vide et `vanished_word` vaut "" côté écran public.
export type VanishingWordState = {
  phase: 'idle' | 'memorizing' | 'vanished' | 'claimed' | 'revealed' | 'finished';
  round_number: number;
  words: string[];
  remaining_words: string[];
  vanished_word: string;
  reveal_at_ms: number;
  current_buzzer_team: string | null;
  excluded_teams: string[];
  round_winner: string | null;
  scores: Record<string, number>;
  winner_team: string | null;
  memorization_ms: number;
  winning_score: number;
  words_per_list: number;
};

// Jeux « buzze seulement si… » : le serveur juge chaque buzz (+1 / −1, jamais sous 0).
export type BuzzVerdict = {
  team: string;
  correct: boolean;
  points: number;
};

export type BuzzStreamGame<Verdict extends BuzzVerdict = BuzzVerdict> = {
  phase: 'idle' | 'running' | 'feedback' | 'paused' | 'finished';
  shown_at_ms: number;
  deadline_ms: number;
  verdict: Verdict | null;
  scores: Record<string, number>;
  winner_team: string | null;
  feedback_ms: number;
  winning_score: number;
  // Pause déclenchée par le serveur après `auto_pause_after` éléments d'affilée sans buzz.
  auto_paused: boolean;
  auto_pause_after: number;
};

export type FlashCalcVerdict = BuzzVerdict & {
  expression: string;
  shown_result: number;
  true_result: number;
};

// Le serveur ne révèle jamais si le calcul affiché est juste : seul `verdict` le dit, après un buzz.
export type FlashCalcState = BuzzStreamGame<FlashCalcVerdict> & {
  calc_number: number;
  expression: string;
  shown_result: number;
  level: number;
  max_level: number;
  calcs_per_level: number;
  calc_duration_ms: number;
};

export type RightFlagVerdict = BuzzVerdict & {
  flag_code: string;
  flag_country: string;
};

// `country_code` (le bon drapeau) vaut "" côté écran public tant qu'il n'est ni trouvé ni révélé.
export type RightFlagState = BuzzStreamGame<RightFlagVerdict> & {
  round_number: number;
  country_code: string;
  country_name: string;
  flag_index: number;
  flag_code: string;
  answer_revealed: boolean;
  flag_number: number;
  flags_per_round: number;
};

export type FamilyAnswer = { text: string; points: number };

export type FamilyBoardSlot = { revealed: boolean; found_by: string | null };

// Côté écran public, une réponse non retournée arrive vide : { text: "", points: 0 }.
export type GoldenFamilyState = {
  phase: 'idle' | 'faceoff' | 'duel' | 'control' | 'steal' | 'revealed' | 'finished';
  question_number: number;
  question: { id: string; text: string; answers: FamilyAnswer[] } | null;
  board: FamilyBoardSlot[];
  current_team: string | null;
  control_team: string | null;
  steal_from: string | null;
  strikes: number;
  pending_teams: string[];
  turn: number;
  misses: number;
  scores: Record<string, number>;
  winner_team: string | null;
  winning_score: number;
  max_strikes: number;
};

// `current_card` est toujours null côté écran public : le mot reste secret sur la régie.
export type ForbiddenWordState = {
  phase: 'idle' | 'ready' | 'running' | 'finished';
  turn_order: string[];
  turns: ForbiddenWordTurn[];
  current_card: null;
  current_team: string | null;
  started_at_ms: number;
  deadline_at_ms: number;
  turn_duration_ms: number;
  scores: Record<string, number>;
  // Égalité en tête : les équipes concernées rejouent 20 s chacune, jusqu'à les départager.
  sudden_death_round: number;
  sudden_death_teams: string[];
  winner_team: string | null;
};

export type GameSession = {
  active_round: ActiveRound | null;
  blindtest: BlindtestState;
  stopchrono: StopChronoState;
  culture: CultureState;
  bombe: BombeState;
  memory: MemoryState;
  seven_differences: SevenDifferencesState;
  auction: AuctionState;
  forbidden_word: ForbiddenWordState;
  vanishing_word: VanishingWordState;
  flash_calc: FlashCalcState;
  right_flag: RightFlagState;
  golden_family: GoldenFamilyState;
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
