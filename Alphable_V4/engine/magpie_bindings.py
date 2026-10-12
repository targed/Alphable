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

from alphable_v4.engine.move import Move
from alphable_v4.engine.game_state import GameState


# Exit code enum from src/impl/cmd_api.h
MAGPIE_SUCCESS = 0
MAGPIE_ERROR = 1
MAGPIE_DID_NOT_RUN = 2


def find_libmagpie() -> str:
    """Finds the libmagpie.so shared library file."""
    # Search common relative locations
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "..", "vendor", "magpie", "bin", "libmagpie.so"),
        os.path.join(base_dir, "..", "vendor", "magpie", "bin", "libmagpie.dylib"),
        os.path.join(base_dir, "libmagpie.so"),
        "/usr/local/lib/libmagpie.so",
    ]
    for c in candidates:
        norm = os.path.normpath(c)
        if os.path.exists(norm):
            return norm

    raise FileNotFoundError(
        "Could not find libmagpie.so. Please run 'make libmagpie' inside vendor/magpie."
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
        cdll.magpie_get_last_command_output.restype = ctypes.c_char_p

        # void magpie_free_string(char *str);
        cdll.magpie_free_string.argtypes = [ctypes.c_char_p]
        cdll.magpie_free_string.restype = None

        # bool magpie_has_error(const Magpie *mp);
        cdll.magpie_has_error.argtypes = [ctypes.c_void_p]
        cdll.magpie_has_error.restype = ctypes.c_bool

        # char *magpie_get_and_clear_error(Magpie *mp);
        cdll.magpie_get_and_clear_error.argtypes = [ctypes.c_void_p]
        cdll.magpie_get_and_clear_error.restype = ctypes.c_char_p

        # char *magpie_get_last_command_status_message(Magpie *mp);
        cdll.magpie_get_last_command_status_message.argtypes = [ctypes.c_void_p]
        cdll.magpie_get_last_command_status_message.restype = ctypes.c_char_p

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
    ):
        self._ctypes = MagpieCtypes(lib_path=lib_path)

        if data_dir is None:
            # Default to vendor/magpie/data
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.normpath(
                os.path.join(base_dir, "..", "vendor", "magpie", "data")
            )

        self.data_dir = data_dir
        self.lexicon = lexicon
        self.use_wmp = use_wmp

        data_bytes = self.data_dir.encode("utf-8")
        self._handle = self._ctypes._cdll.magpie_create_with_options(
            data_bytes, None, self.use_wmp
        )

        if not self._handle:
            raise RuntimeError("Failed to allocate Magpie instance")

        if self._ctypes._cdll.magpie_has_error(self._handle):
            err_ptr = self._ctypes._cdll.magpie_get_and_clear_error(self._handle)
            err_msg = err_ptr.decode("utf-8") if err_ptr else "Unknown error"
            self._ctypes._cdll.magpie_destroy(self._handle)
            self._handle = None
            raise RuntimeError(f"Failed to initialize MAGPIE: {err_msg}")

        # Set default lexicon and output settings for clean machine-readable move generation
        if lexicon:
            self.set_lexicon(lexicon)
        self._current_numplays = 100
        self.run_command(f"set -shwithmoves false -numplays {self._current_numplays} -maxnumdplays {self._current_numplays}")

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
                if err_ptr:
                    err_msg = err_ptr.decode("utf-8")
            raise RuntimeError(f"MAGPIE command '{cmd}' failed (code {ret}): {err_msg}")

        out_ptr = self._ctypes._cdll.magpie_get_last_command_output(self._handle)
        output = out_ptr.decode("utf-8") if out_ptr else ""
        return output

    def set_lexicon(self, lexicon: str) -> None:
        """Switches current lexicon (e.g. 'CSW24', 'NWL23', 'CSW21')."""
        self.run_command(f"set -lex {lexicon}")
        self.lexicon = lexicon

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
