"""
Alphable Online Gaming Platform Integration.
Provides extensible adapters for online Scrabble platforms (Woogles, etc.).
"""

from alphable.platform.base import (
    AbstractPlatformAdapter,
    OnlineGameState,
    PlatformGameConfig,
    PlatformMove,
)

__all__ = [
    "AbstractPlatformAdapter",
    "OnlineGameState",
    "PlatformGameConfig",
    "PlatformMove",
]
