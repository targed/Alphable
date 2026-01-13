// Type definitions for Alphable game data

export interface GameTurn {
  turn_index: number;
  player: number;
  action_type: "PLAY" | "PASS" | "EXCHANGE";
  action_id: number;
  score: number;
  tiles_in_bag: number;
  consecutive_passes: number;
  word?: string;
  position?: [number, number]; // [row, col]
  direction?: "Across" | "Down";
  rack_before?: string[];
  rack_after?: string[];
  board_state?: string;
}

export interface GameMetadata {
  checkpoint?: number;
  opponent?: string;
  simulations?: number;
  match_type?: string;
  [key: string]: any;
}

export interface GameData {
  game_id: string;
  timestamp: string;
  player_names: [string, string];
  final_score: [number, number];
  metadata: GameMetadata;
  turns: GameTurn[];
}

export interface GameListItem {
  id: string;
  filename: string;
  category: string;
  path: string;
  timestamp: string;
  player_names: [string, string];
  final_score: [number, number];
  total_turns: number;
  metadata: GameMetadata;
}

export interface PlayerStats {
  name: string;
  total_moves: number;
  plays: number;
  passes: number;
  exchanges: number;
  bingos: number;
  bingo_words: string[];
  total_score: number;
  average_score_per_move: number;
  highest_scoring_move: number;
  final_score: number;
}

export interface GameStats {
  total_turns: number;
  player_stats: [PlayerStats, PlayerStats];
}

export type PremiumSquareType = "TW" | "DW" | "TL" | "DL" | null;

export interface BoardSquare {
  row: number;
  col: number;
  letter: string | null;
  premium: PremiumSquareType;
  isNew: boolean; // Highlight newly placed tiles
}
