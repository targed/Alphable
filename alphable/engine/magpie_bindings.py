"""
ctypes bindings for the MAGPIE C Scrabble engine (libmagpie.so).

Provides direct Python access to MAGPIE's move generation, KLV static equity evaluation,
CGP game state loading, and endgame solvers.
"""

from __future__ import annotations
import ctypes
import os
import sys
from typing import List, Optional, Tuple, Dict, Any

from alphable.engine.move import Move
from alphable.engine.game_state import GameState


# Exit code enum from src/impl/cmd_api.h
MAGPIE_SUCCESS = 0
MAGPIE_ERROR = 1
MAGPIE_DID_NOT_RUN = 2


def find_libmagpie() -> str:
    """Finds the libmagpie.so shared library file across common relative locations."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    real_dir = os.path.dirname(os.path.realpath(__file__))
    cwd = os.getcwd()

    candidates = [
        # Relative to alphable/engine: root vendor/
        os.path.join(base_dir, "..", "..", "vendor", "magpie", "bin", "libmagpie.so"),
        os.path.join(base_dir, "..", "..", "vendor", "magpie", "bin", "libmagpie.dylib"),
        os.path.join(real_dir, "..", "..", "vendor", "magpie", "bin", "libmagpie.so"),
        os.path.join(real_dir, "..", "..", "vendor", "magpie", "bin", "libmagpie.dylib"),
        # Relative to current working directory
        os.path.join(cwd, "vendor", "magpie", "bin", "libmagpie.so"),
        os.path.join(cwd, "vendor", "magpie", "bin", "libmagpie.dylib"),
        # Fallback in engine directory or system paths
        os.path.join(base_dir, "libmagpie.so"),
        "/usr/local/lib/libmagpie.so",
    ]
    for c in candidates:
        norm = os.path.normpath(c)
        if os.path.exists(norm):
            return norm

    raise FileNotFoundError(
        "Could not find libmagpie.so (or libmagpie.dylib). Please run 'make libmagpie' inside vendor/magpie "
        "or execute ./install.sh to automatically compile it."
    )


class MagpieCtypes:
    """Low-level ctypes function wrapper for libmagpie.so."""

    def __init__(self, lib_path: Optional[str] = None):
        if lib_path is None:
            lib_path = find_libmagpie()

        self.lib_path = lib_path
        self._cdll = ctypes.CDLL(lib_path)
        self._setup_prototypes()

    def _setup_prototypes(self):
        cdll = self._cdll

        # Magpie *magpie_create(const char *data_paths);
        cdll.magpie_create.argtypes = [ctypes.c_char_p]
        cdll.magpie_create.restype = ctypes.c_void_p

        # Magpie *magpie_create_with_options(const char *data_paths, const char *settings_filename, bool use_wmp);
        cdll.magpie_create_with_options.argtypes = [
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_bool,
        ]
        cdll.magpie_create_with_options.restype = ctypes.c_void_p

        # void magpie_destroy(Magpie *mp);
        cdll.magpie_destroy.argtypes = [ctypes.c_void_p]
        cdll.magpie_destroy.restype = None

        # cmd_exit_code magpie_run_sync(Magpie *mp, const char *command);
        cdll.magpie_run_sync.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        cdll.magpie_run_sync.restype = ctypes.c_int

        # cmd_exit_code magpie_run_sync_human_readable(Magpie *mp, const char *command);
        cdll.magpie_run_sync_human_readable.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
        ]
        cdll.magpie_run_sync_human_readable.restype = ctypes.c_int

        # char *magpie_get_last_command_output(const Magpie *mp);
        cdll.magpie_get_last_command_output.argtypes = [ctypes.c_void_p]
        cdll.magpie_get_last_command_output.restype = ctypes.c_void_p

        # void magpie_free_string(char *str);
        cdll.magpie_free_string.argtypes = [ctypes.c_void_p]
        cdll.magpie_free_string.restype = None

        # bool magpie_has_error(const Magpie *mp);
        cdll.magpie_has_error.argtypes = [ctypes.c_void_p]
        cdll.magpie_has_error.restype = ctypes.c_bool

        # char *magpie_get_and_clear_error(Magpie *mp);
        cdll.magpie_get_and_clear_error.argtypes = [ctypes.c_void_p]
        cdll.magpie_get_and_clear_error.restype = ctypes.c_void_p

        # char *magpie_get_last_command_status_message(Magpie *mp);
        cdll.magpie_get_last_command_status_message.argtypes = [ctypes.c_void_p]
        cdll.magpie_get_last_command_status_message.restype = ctypes.c_void_p

        # void magpie_stop_current_command(Magpie *mp);
        cdll.magpie_stop_current_command.argtypes = [ctypes.c_void_p]
        cdll.magpie_stop_current_command.restype = None


class MagpieEngine:
    """
    High-level Python interface to MAGPIE.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        lexicon: str = "CSW24",
        lib_path: Optional[str] = None,
        use_wmp: bool = False,
        use_pat: bool = False,
    ):
        self._ctypes = MagpieCtypes(lib_path=lib_path)

        if data_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            real_dir = os.path.dirname(os.path.realpath(__file__))
            cwd = os.getcwd()
            candidates = [
                os.path.join(base_dir, "..", "..", "vendor", "magpie", "data"),
                os.path.join(real_dir, "..", "..", "vendor", "magpie", "data"),
                os.path.join(cwd, "vendor", "magpie", "data"),
            ]
            for c in candidates:
                norm = os.path.normpath(c)
                if os.path.isdir(norm):
                    data_dir = norm
                    break
            if data_dir is None:
                data_dir = os.path.normpath(os.path.join(base_dir, "..", "..", "vendor", "magpie", "data"))

        self.data_dir = data_dir
        self.lexicon = lexicon
        self.use_wmp = use_wmp
        self.use_pat = use_pat

        data_bytes = self.data_dir.encode("utf-8")
        self._handle = self._ctypes._cdll.magpie_create_with_options(
            data_bytes, None, self.use_wmp
        )

        if not self._handle:
            raise RuntimeError("Failed to allocate Magpie instance")

        if self._ctypes._cdll.magpie_has_error(self._handle):
            err_ptr = self._ctypes._cdll.magpie_get_and_clear_error(self._handle)
            err_msg = self._take_string(err_ptr) if err_ptr else "Unknown error"
            self._ctypes._cdll.magpie_destroy(self._handle)
            self._handle = None
            raise RuntimeError(f"Failed to initialize MAGPIE: {err_msg}")

        # Set default lexicon and output settings for clean machine-readable move generation
        if lexicon:
            self.set_lexicon(lexicon)
            if self.use_pat:
                self.set_pat(lexicon)
        threads = int(os.environ.get("MAGPIE_THREADS", "1"))
        self._current_numplays = 100
        self.run_command(f"set -shwithmoves false -numplays {self._current_numplays} -maxnumdplays {self._current_numplays} -ttfraction 0.05 -threads {threads}")

    def __enter__(self) -> MagpieEngine:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Releases the C engine instance."""
        if self._handle is not None:
            self._ctypes._cdll.magpie_destroy(self._handle)
            self._handle = None

    def __del__(self):
        self.close()

    def _take_string(self, ptr: Optional[int]) -> str:
        """Copies a C string returned by libmagpie and immediately frees the C heap allocation."""
        if not ptr:
            return ""
        val = ctypes.string_at(ptr).decode("utf-8")
        self._ctypes._cdll.magpie_free_string(ptr)
        return val

    def run_command(self, cmd: str, human_readable: bool = False) -> str:
        """Runs a MAGPIE console command synchronously and returns the output string."""
        if not self._handle:
            raise RuntimeError("Magpie instance has been closed")

        cmd_bytes = cmd.strip().encode("utf-8")
        if human_readable:
            ret = self._ctypes._cdll.magpie_run_sync_human_readable(
                self._handle, cmd_bytes
            )
        else:
            ret = self._ctypes._cdll.magpie_run_sync(self._handle, cmd_bytes)

        if ret != MAGPIE_SUCCESS:
            err_msg = ""
            if self._ctypes._cdll.magpie_has_error(self._handle):
                err_ptr = self._ctypes._cdll.magpie_get_and_clear_error(self._handle)
                err_msg = self._take_string(err_ptr)
            raise RuntimeError(f"MAGPIE command '{cmd}' failed (code {ret}): {err_msg}")

        out_ptr = self._ctypes._cdll.magpie_get_last_command_output(self._handle)
        return self._take_string(out_ptr)

    def set_lexicon(self, lexicon: str) -> None:
        """Switches current lexicon (e.g. 'CSW24', 'NWL23', 'CSW21')."""
        self.run_command(f"set -lex {lexicon}")
        self.lexicon = lexicon

    def set_pat(self, pat_lexicon: Optional[str] = None) -> None:
        """Enables or disables Positional Adjustment Term (PAT)."""
        if pat_lexicon:
            self.run_command(f"set -pat {pat_lexicon}")
            self.use_pat = True
        else:
            self.run_command("set -pat none")
            self.use_pat = False

    def set_cgp(self, cgp: str) -> None:
        """Sets the current game board and rack state using a CGP string."""
        self.run_command(f"cgp {cgp}")

    def set_rack(self, rack: str) -> None:
        """Sets the player's rack."""
        self.run_command(f"rack {rack}")

    def generate_moves(
        self,
        cgp: Optional[str] = None,
        game_state: Optional[GameState] = None,
        rack: Optional[str] = None,
        max_candidates: Optional[int] = None,
    ) -> List[Move]:
        """
        Generates legal moves for the current position, sorted by static equity descending.

        Args:
            cgp: Optional CGP string to load before generating
            game_state: Optional GameState to load via CGP before generating
            rack: Optional rack string to set before generating
            max_candidates: Optional maximum candidates to generate (defaults to 100)
        """
        if max_candidates is not None and max_candidates != self._current_numplays:
            self.run_command(f"set -numplays {max_candidates} -maxnumdplays {max_candidates}")
            self._current_numplays = max_candidates
        if game_state is not None:
            self.set_cgp(game_state.to_cgp())
        elif cgp is not None:
            self.set_cgp(cgp)

        if rack is not None:
            self.set_rack(rack)

        output = self.run_command("generate")
        moves: List[Move] = []
        for line in output.splitlines():
            m = Move.from_ucgi_line(line)
            if m is not None:
                moves.append(m)

        return moves

    def best_reply(self, game_state: GameState, opp_rack: str) -> Optional[Move]:
        """
        Calculates the opponent's best static-equity reply given their rack.
        """
        # Build opponent position: opponent is Player 1 in the new state
        opp_state = GameState(
            board=game_state.board,
            rack=list(opp_rack.upper()),
            opp_rack=game_state.rack,
            score=game_state.opp_score,
            opp_score=game_state.score,
            scoreless_turns=game_state.scoreless_turns,
            bag_count=game_state.bag_count,
            lexicon=game_state.lexicon,
        )
        replies = self.generate_moves(game_state=opp_state)
        return replies[0] if replies else None

    def solve_endgame(self, cgp: Optional[str] = None) -> str:
        """Solves the endgame using MAGPIE's exact alpha-beta solver."""
        if cgp is not None:
            self.set_cgp(cgp)
        return self.run_command("endgame")

    def simulate(self, iterations: int = 50) -> str:
        """Runs Monte Carlo simulation lookahead over generated candidates."""
        self.run_command(f"set -iterations {iterations}")
        return self.run_command("simulate")

    def simulate_candidates(
        self,
        iterations: int = 25,
        candidate_moves: Optional[List[Move]] = None,
        game_state: Optional[GameState] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs native C Monte Carlo simulation rollouts and returns parsed candidate moves
        with their simulated return equity, win probability, and spread.

        Args:
            iterations: Number of Monte Carlo rollout iterations per candidate in C (~98k nps).
            candidate_moves: Optional pre-generated list of Move objects to match against.
            game_state: Optional GameState to set before simulation.

        Returns:
            List of dictionaries:
            [{
                "rank": int,
                "move": Move,
                "score": int,
                "sim_equity": float,
                "win_prob": float,
                "spread": float,
                "raw_line": str
            }, ...]
        """
        if game_state is not None:
            self.set_cgp(game_state.to_cgp())
            if candidate_moves is None:
                candidate_moves = self.generate_moves(max_candidates=15)
            else:
                self.run_command("generate")
        elif candidate_moves is None:
            candidate_moves = self.generate_moves(max_candidates=15)

        if not candidate_moves:
            return []

        # Configure iterations and run native simulation
        self.run_command(f"set -iterations {iterations}")
        try:
            raw_output = self.run_command("simulate")
        except Exception:
            return []

        results: List[Dict[str, Any]] = []
        for line in raw_output.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue

            # Format: '1:   8F STARNIE        66 - 69.13 0.6156 25.13 ...'
            parts = line.split(":", 1)
            rank_str = parts[0].strip()
            if not rank_str.isdigit():
                continue

            rank = int(rank_str)
            tokens = parts[1].strip().split()
            if len(tokens) < 4:
                continue

            coord_token = tokens[0].upper()
            word_token = tokens[1].replace("(", "").replace(")", "").upper()
            
            # Find score (the integer immediately before '-')
            dash_idx = -1
            for idx, tok in enumerate(tokens):
                if tok == "-":
                    dash_idx = idx
                    break

            score_val = 0
            if dash_idx > 0 and tokens[dash_idx - 1].lstrip("-").isdigit():
                score_val = int(tokens[dash_idx - 1])
            elif len(tokens) >= 3 and tokens[2].lstrip("-").isdigit():
                score_val = int(tokens[2])

            win_pct = 50.0
            win_sem = 0.0
            sim_equity = 0.0
            equity_sem = 0.0
            static_equity = 0.0

            if dash_idx != -1:
                # Column 1 after dash: win percentage (0 to 100%)
                if dash_idx + 1 < len(tokens):
                    try:
                        win_pct = float(tokens[dash_idx + 1])
                    except ValueError:
                        pass
                # Column 2 after dash: win percentage SEM
                if dash_idx + 2 < len(tokens):
                    try:
                        win_sem = float(tokens[dash_idx + 2])
                    except ValueError:
                        pass
                # Column 3 after dash: simulated equity spread (points)
                if dash_idx + 3 < len(tokens):
                    try:
                        sim_equity = float(tokens[dash_idx + 3])
                    except ValueError:
                        pass
                # Column 4 after dash: simulated equity SEM
                if dash_idx + 4 < len(tokens):
                    try:
                        equity_sem = float(tokens[dash_idx + 4])
                    except ValueError:
                        pass
                # Column 5 after dash: static equity
                if dash_idx + 5 < len(tokens):
                    try:
                        static_equity = float(tokens[dash_idx + 5])
                    except ValueError:
                        pass

            win_prob = win_pct / 100.0

            # Match against candidate_moves
            matched_move = None
            for c in candidate_moves:
                if c.coord_str.upper() == coord_token and c.word.upper() == word_token:
                    matched_move = c
                    break

            # Secondary match: coord and score
            if matched_move is None and score_val is not None:
                for c in candidate_moves:
                    if c.coord_str.upper() == coord_token and c.score == score_val:
                        matched_move = c
                        break

            # If still unmatched, construct Move object from parsed tokens
            if matched_move is None:
                try:
                    if coord_token in ("PASS", "-"):
                        matched_move = Move.create_pass()
                    elif coord_token.startswith("-"):
                        # Exchange
                        matched_move = Move(
                            row=0, col=0, direction="Across", word="",
                            score=0, is_exchange=True, letters_exchanged=list(coord_token[1:])
                        )
                    else:
                        matched_move = Move.from_coordinates(
                            coord_str=coord_token,
                            word=word_token,
                            score=score_val or 0,
                            equity=sim_equity,
                        )
                except Exception:
                    continue

            results.append({
                "rank": rank,
                "move": matched_move,
                "score": matched_move.score if matched_move else (score_val or 0),
                "sim_equity": sim_equity,
                "win_prob": win_prob,
                "win_pct": win_pct,
                "win_sem": win_sem,
                "sim_sem": equity_sem,
                "static_equity": static_equity,
                "spread": sim_equity,
                "raw_line": line,
            })

        return results

    def solve_endgame_move(
        self,
        game_state: Optional[GameState] = None,
        candidate_moves: Optional[List[Move]] = None,
    ) -> Optional[Move]:
        """
        Solves the endgame using MAGPIE's exact alpha-beta solver and returns
        the optimal Move object.
        """
        if game_state is not None:
            self.set_cgp(game_state.to_cgp())

        try:
            raw_output = self.solve_endgame()
        except Exception:
            return None

        lines = [l.strip() for l in raw_output.splitlines() if l.strip()]
        for line in lines:
            if line.startswith("Endgame") or line.startswith("Play") or "nodes" in line.lower():
                continue
            parts = line.split()
            if len(parts) >= 2:
                coord = parts[0].upper()
                clean_word = parts[1].replace("(", "").replace(")", "").upper()
                score = int(parts[2]) if len(parts) >= 3 and parts[2].lstrip("-").isdigit() else 0

                if candidate_moves:
                    # Primary pass: exact coordinate and word match
                    for c in candidate_moves:
                        if c.coord_str.upper() == coord and c.word.upper() == clean_word:
                            return c
                    # Secondary pass: coordinate and score match
                    for c in candidate_moves:
                        if c.coord_str.upper() == coord and c.score == score:
                            return c

                try:
                    if coord == "PASS":
                        return Move.create_pass()
                    return Move.from_coordinates(coord_str=coord, word=clean_word, score=score)
                except Exception:
                    continue

        return None

