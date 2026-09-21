"""
Base abstractions and data structures for online Scrabble platform adapters.
Designed to be platform-agnostic (supports Woogles, ISC, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class OnlineGameState:
    """Snapshot of an online game's active state."""
    board: List[List[str]]                      # 15x15 grid, '.' for empty, 'A'-'Z' (lower for blanks)
    rack: List[str]                             # Current player's rack tiles (e.g. ['A', 'B', '?'])
    my_score: int = 0
    opponent_score: int = 0
    my_name: str = "Alphable"
    opponent_name: str = "Opponent"
    is_my_turn: bool = False
    bag_remaining: int = 86
    my_time_remaining: float = 900.0            # Seconds remaining on clock
    opponent_time_remaining: float = 900.0
    turn_number: int = 1
    is_game_over: bool = False
    winner: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformGameConfig:
    """Configuration used to establish or join an online game."""
    opponent_type: str = "bot"                  # "bot" or "human"
    bot_name: str = "HastyBot"                  # "HastyBot", "BestBot", "BeginnerBot"
    dictionary: str = "CSW24"                   # "CSW24" or "NWL23"
    game_mode: str = "realtime"                 # "realtime" or "correspondence"
    time_control: str = "15+0"                  # "15+0", "5+0", "3+0"
    rated: bool = False
    challenge_user: Optional[str] = None


@dataclass
class PlatformMove:
    """Representation of an action to submit on the platform."""
    action: str = "PLAY"                        # "PLAY", "PASS", "EXCHANGE"
    word: Optional[str] = None                  # Word to play
    row: Optional[int] = None                   # 0-indexed row (0-14)
    col: Optional[int] = None                   # 0-indexed col (0-14)
    direction: Optional[str] = None             # "Across" or "Down"
    tiles_to_exchange: Optional[List[str]] = None


class AbstractPlatformAdapter(ABC):
    """
    Abstract Base Class for Scrabble platform adapters.
    Encapsulates browser automation, network telemetry, and DOM interaction.
    """

    @abstractmethod
    def start(self, headless: bool = False, user_data_dir: Optional[str] = None) -> None:
        """Launch the browser environment and connect to the platform."""
        pass

    @abstractmethod
    def ensure_logged_in(self) -> str:
        """Ensure an authenticated or valid guest session exists. Returns username."""
        pass

    @abstractmethod
    def create_game(self, config: PlatformGameConfig) -> str:
        """Create or initiate a game match. Returns game URL or ID."""
        pass

    @abstractmethod
    def get_game_state(self) -> OnlineGameState:
        """Scrape or read current live game state from the board and UI."""
        pass

    @abstractmethod
    def wait_for_my_turn(self, poll_interval: float = 0.5, timeout: float = 300.0) -> OnlineGameState:
        """Block until it is Alphable's turn to play, or until the game ends."""
        pass

    @abstractmethod
    def play_move(self, move: PlatformMove) -> bool:
        """Submit a move (PLAY, PASS, or EXCHANGE) on the platform."""
        pass

    @abstractmethod
    def is_game_over(self) -> bool:
        """Check if the current match has completed."""
        pass

    @abstractmethod
    def get_final_result(self) -> Dict[str, Any]:
        """Fetch final game outcome, scores, and replay metadata."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Cleanly terminate browser session."""
        pass
