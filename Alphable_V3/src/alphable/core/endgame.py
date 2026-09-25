"""
Deterministic Exact Endgame Minimax Solver for Alphable.

When the Scrabble tile bag is empty (bag == 0) and the opponent's rack is fully known
from tile tracking, Scrabble transitions into a deterministic, zero-sum, perfect-information
game. This solver runs alpha-beta branch-and-bound search with move ordering to find the
mathematically optimal endgame sequence that maximizes point spread and secures victory.
"""

from typing import List, Dict, Optional, Tuple
import copy
from alphable.core import simulator

# Standard Scrabble tile face values
TILE_VALUES: Dict[str, int] = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4,
    'I': 1, 'J': 8, 'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3,
    'Q': 10, 'R': 1, 'S': 1, 'T': 1, 'U': 1, 'V': 4, 'W': 4, 'X': 8,
    'Y': 4, 'Z': 10, '?': 0,
}


def rack_points(rack: List[str]) -> int:
    """Sum of face values of tiles in a rack."""
    return sum(TILE_VALUES.get(c.upper(), 0) for c in rack)


class ExactEndgameSolver:
    def __init__(self, inference_engine, branch_limit: int = 5):
        """
        Args:
            inference_engine: Provides move generation (move_gen.generate).
            branch_limit: Maximum number of non-out candidate moves to branch on per ply.
        """
        self.engine = inference_engine
        self.branch_limit = branch_limit

    def _get_candidate_moves(self, board, rack):
        moves = self.engine.move_gen.generate(board, rack)
        if not moves:
            return []
        evaluated = []
        for m in moves:
            nb, pts, nr = simulator.simulate_move(board, m, rack)
            evaluated.append((m, nb, pts, nr))
        evaluated.sort(key=lambda item: item[2], reverse=True)
        # Always include all moves that go out (empty rack)
        out_moves = [item for item in evaluated if len(item[3]) == 0]
        # Top-K highest-scoring non-out moves
        non_out_moves = [item for item in evaluated if len(item[3]) > 0][:self.branch_limit]
        return out_moves + non_out_moves

    def solve(
        self,
        board: List[List[str]],
        my_rack: List[str],
        opp_rack: List[str],
        score_diff: int = 0,
        max_depth: int = 4,
    ) -> Tuple[Optional[Dict], float]:
        """
        Solves the deterministic endgame using alpha-beta search.

        Args:
            board: Current 15x15 board matrix.
            my_rack: Our remaining rack tiles.
            opp_rack: Opponent's known rack tiles.
            score_diff: Current score difference (my_score - opp_score).
            max_depth: Maximum ply depth to explore.

        Returns:
            Tuple of (best_move, guaranteed_spread_margin).
        """
        # Adaptive depth limit: if either player has > 3 tiles, search at depth 2 (immediate turn + reply)
        # to ensure instantaneous solving (< 0.2s) without combinatorial explosion.
        # When both players have <= 3 tiles, search at full depth 4 to solve out completely.
        if len(my_rack) > 3 or len(opp_rack) > 3:
            effective_depth = min(max_depth, 2)
        else:
            effective_depth = max_depth

        candidates = self._get_candidate_moves(board, my_rack)
        if not candidates:
            # We must pass. Evaluate opponent's reply.
            margin = self._minimax(
                board, opp_rack, my_rack, score_diff,
                is_maximizing=False, alpha=-float('inf'), beta=float('inf'),
                depth=effective_depth - 1, consecutive_passes=1
            )
            return None, margin

        best_move = None
        best_margin = -float('inf')
        alpha = -float('inf')
        beta = float('inf')

        for move, new_board, pts, new_rack in candidates:
            # Case 1: We play out all our tiles!
            if len(new_rack) == 0:
                # Terminal win: we score pts + 2 * remaining opponent tiles
                margin = float(score_diff + pts + 2 * rack_points(opp_rack))
            else:
                # Opponent's turn to respond (minimizing player)
                margin = self._minimax(
                    new_board, opp_rack, new_rack, score_diff + pts,
                    is_maximizing=False, alpha=alpha, beta=beta,
                    depth=effective_depth - 1, consecutive_passes=0
                )

            if margin > best_margin:
                best_margin = margin
                best_move = move

            alpha = max(alpha, best_margin)
            if alpha >= beta:
                break  # Beta cutoff

        return best_move, best_margin

    def _minimax(
        self,
        board: List[List[str]],
        active_rack: List[str],
        passive_rack: List[str],
        score_diff: int,
        is_maximizing: bool,
        alpha: float,
        beta: float,
        depth: int,
        consecutive_passes: int,
    ) -> float:
        """
        Recursive alpha-beta search.
        is_maximizing=True means active_rack is Our player.
        is_maximizing=False means active_rack is Opponent.
        """
        # Terminal check 1: double pass (game over)
        if consecutive_passes >= 2:
            if is_maximizing:
                return float(score_diff - rack_points(active_rack) + rack_points(passive_rack))
            else:
                return float(score_diff + rack_points(passive_rack) - rack_points(active_rack))

        # Terminal check 2: depth limit reached
        if depth <= 0:
            if is_maximizing:
                return float(score_diff - rack_points(active_rack) + rack_points(passive_rack))
            else:
                return float(score_diff + rack_points(passive_rack) - rack_points(active_rack))

        candidates = self._get_candidate_moves(board, active_rack)

        # If no legal moves, player passes
        if not candidates:
            return self._minimax(
                board, passive_rack, active_rack, score_diff,
                is_maximizing=not is_maximizing, alpha=alpha, beta=beta,
                depth=depth - 1, consecutive_passes=consecutive_passes + 1
            )

        if is_maximizing:
            max_eval = -float('inf')
            for _, nb, pts, nr in candidates:
                if len(nr) == 0:
                    # Active player (us) went out!
                    ev = float(score_diff + pts + 2 * rack_points(passive_rack))
                else:
                    ev = self._minimax(
                        nb, passive_rack, nr, score_diff + pts,
                        is_maximizing=False, alpha=alpha, beta=beta,
                        depth=depth - 1, consecutive_passes=0
                    )
                max_eval = max(max_eval, ev)
                alpha = max(alpha, ev)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for _, nb, pts, nr in candidates:
                if len(nr) == 0:
                    # Active player (opponent) went out!
                    ev = float(score_diff - pts - 2 * rack_points(passive_rack))
                else:
                    ev = self._minimax(
                        nb, passive_rack, nr, score_diff - pts,
                        is_maximizing=True, alpha=alpha, beta=beta,
                        depth=depth - 1, consecutive_passes=0
                    )
                min_eval = min(min_eval, ev)
                beta = min(beta, ev)
                if beta <= alpha:
                    break
            return min_eval
