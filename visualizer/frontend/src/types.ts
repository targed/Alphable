/**
 * Alphable Visualizer Studio Domain Types
 */

export type CellValue = string | null;
export type BoardState = CellValue[][];

export interface Move {
  word: string;
  row: number;
  col: number;
  direction: "Across" | "Down";
  coord?: string;
  points?: number;
}

export interface CandidateMove {
  word: string;
  row: number;
  col: number;
  direction: "Across" | "Down";
  coord: string;
  points: number;
  equity: number;
  leave?: string;
  bams_score?: number;
  value?: number;
  is_play?: boolean;
  is_exchange?: boolean;
  is_pass?: boolean;
}

export interface EngineInfo {
  id: string;
  name: string;
  description: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  status: string;
  description: string;
  verified_wr?: string;
  size_mb?: number;
}

export interface TurnData {
  turn_index?: number;
  player: number; // 0 or 1
  action_type: "PLAY" | "EXCHANGE" | "PASS";
  score: number;
  total_score?: number;
  tiles_in_bag?: number;
  word?: string;
  position?: [number, number];
  direction?: string;
  rack_before?: string[];
  rack_after?: string[];
  board_state?: string;
  top_candidates?: any[];
}

export interface GameSummary {
  id: string;
  filename: string;
  category: string;
  engine: string;
  timestamp: string;
  player_names: string[];
  final_score: number[];
  score_margin: number;
  winner: string;
  bingos: number;
  total_turns: number;
  metadata?: Record<string, any>;
}

export interface TournamentSummary {
  run_id: string;
  filename: string;
  timestamp: string;
  mode: string;
  tag?: string;
  lexicon: string;
  total_games: number;
  duplicate_pairs?: number | null;
  duration_seconds: number;
  seconds_per_game: number;
  player1: {
    name: string;
    short_name: string;
    spec: string;
    mean_score: number;
    bingos_per_game: number;
    wins: number;
  };
  player2: {
    name: string;
    short_name: string;
    spec: string;
    mean_score: number;
    bingos_per_game: number;
    wins: number;
  };
  draws: number;
  win_rate: {
    percentage: number;
    ci95?: number;
  };
  net_spread: {
    mean: number;
    ci95?: number;
  };
}

export interface ComparisonResult {
  name: string;
  action: string;
  move: Move;
  points: number;
  equity: number;
  candidates_top3: CandidateMove[];
  error?: string;
}

export interface GameSnapshot {
  board: BoardState;
  p1Rack: string[];
  p2Rack: string[];
  p1Score: number;
  p2Score: number;
  bag: string[];
  activePlayer: number;
  lastMove: {
    player: number;
    word: string;
    coord: string;
    points: number;
    action: string;
  } | null;
  turnNumber: number;
  isGameOver?: boolean;
  gameOverReason?: string | null;
  consecutivePasses?: number;
}


export interface PlayerConfig {
  type: "human" | "ai";
  engine: string; // 'v4', 'v3', 'magpie', 'greedy'
  model: string;
  name: string;
}
