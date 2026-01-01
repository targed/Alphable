# Requirements Document: Scrabble Engine Fixes

## Introduction

This specification addresses critical issues in the Scrabble game engine implementation that prevent proper gameplay. The engine currently exhibits three major problems: negative final scores, repeated/stuck moves, and invalid word overlaps. These issues violate the official Scrabble rules as defined in the NASPA Official Tournament Rules (December 2016) and prevent the AlphaZero training from learning proper Scrabble strategy.

The fixes will ensure the engine conforms to official Scrabble rules, provides proper scoring, prevents move repetition, and handles word validation correctly.

## Glossary

- **System**: The Scrabble game engine implementation in `scrabble.py`
- **Move_Generator**: The GADDAG-based move generation system in `structure.py`
- **Agent**: An AI player using AlphaZero to learn Scrabble strategy
- **Rack**: The set of tiles (up to 7) that a player currently holds
- **Board**: The 15x15 grid where tiles are placed
- **Bag**: The collection of undrawn tiles
- **GADDAG**: A data structure for efficient word generation and validation
- **Action_ID**: An integer representing a specific move (row, column, direction)
- **Banned_Actions**: A set of action IDs that have failed validation in the current turn
- **Cross_Word**: A word formed perpendicular to the main word being played
- **Premium_Square**: A board square that multiplies letter or word scores (DL, TL, DW, TW)
- **Hallucination**: When an agent attempts to play a move that doesn't exist in the legal move set
- **Invalid_Move**: A move that violates Scrabble rules (connectivity, rack availability, boundaries)
- **Mercy_Rule**: A game termination condition when progress has stalled

## Requirements

### Requirement 1: Eliminate Negative Scores

**User Story:** As a Scrabble player, I want all scores to remain non-negative throughout the game, so that the final scores accurately reflect game performance according to official Scrabble rules.

#### Acceptance Criteria

1. WHEN a player makes an invalid move THEN THE System SHALL apply a penalty that does not cause the player's score to become negative
2. WHEN a player's score would become negative from a penalty THEN THE System SHALL set the score to zero instead
3. WHEN the game ends THEN THE System SHALL ensure both players have non-negative final scores
4. WHEN calculating final scores THEN THE System SHALL follow official Scrabble scoring rules for unplayed tiles
5. WHEN a player makes a hallucination attempt THEN THE System SHALL apply a penalty proportional to the severity without causing negative scores

### Requirement 2: Prevent Move Repetition and Stuck States

**User Story:** As a game developer, I want the engine to detect and prevent agents from repeatedly attempting the same invalid move, so that games progress normally and training is effective.

#### Acceptance Criteria

1. WHEN an agent attempts the same invalid move three times in a turn THEN THE System SHALL force a pass
2. WHEN a game has no valid progress for 20 turns THEN THE System SHALL terminate the game
3. WHEN both players pass consecutively four times THEN THE System SHALL end the game
4. WHEN the turn count exceeds 100 THEN THE System SHALL terminate the game
5. WHEN an agent is forced to pass due to repeated failures THEN THE System SHALL reset the banned actions for the next turn
6. WHEN a successful move is made THEN THE System SHALL clear the banned actions set

### Requirement 3: Validate Word Formation and Connectivity

**User Story:** As a Scrabble rules enforcer, I want all played words to follow proper connectivity rules, so that only valid Scrabble plays are accepted.

#### Acceptance Criteria

1. WHEN a word is played THEN THE System SHALL verify it connects to at least one existing tile on the board
2. WHEN the first move is played THEN THE System SHALL verify it covers the center square (7,7)
3. WHEN a word is played THEN THE System SHALL verify all tiles are within board boundaries (0-14 for both row and column)
4. WHEN a word is played THEN THE System SHALL verify the player has the required tiles in their rack
5. WHEN a word uses existing board tiles THEN THE System SHALL verify the word matches those tiles exactly
6. WHEN a word is played THEN THE System SHALL verify it forms a single contiguous string in one direction

### Requirement 4: Validate Cross-Word Formation

**User Story:** As a Scrabble player, I want all cross-words formed by my play to be valid words, so that the game follows official Scrabble rules.

#### Acceptance Criteria

1. WHEN a tile is placed adjacent to existing tiles perpendicular to the main word THEN THE System SHALL identify all cross-words formed
2. WHEN cross-words are formed THEN THE System SHALL validate each cross-word against the dictionary
3. WHEN any cross-word is invalid THEN THE System SHALL reject the entire play
4. WHEN a play forms only valid cross-words THEN THE System SHALL calculate and award points for each cross-word
5. WHEN premium squares are used in cross-words THEN THE System SHALL apply multipliers correctly to both the main word and cross-words

### Requirement 5: Implement Proper Scoring

**User Story:** As a Scrabble player, I want my score to accurately reflect the value of my plays according to official Scrabble rules, so that the game is fair and follows standard conventions.

#### Acceptance Criteria

1. WHEN a word is played THEN THE System SHALL calculate the base score using standard tile values
2. WHEN a word uses premium squares THEN THE System SHALL apply letter multipliers before word multipliers
3. WHEN a word uses multiple premium squares THEN THE System SHALL apply all applicable multipliers
4. WHEN a player uses all 7 tiles in one turn THEN THE System SHALL award a 50-point bonus
5. WHEN cross-words are formed THEN THE System SHALL add their scores to the turn total
6. WHEN a blank tile is played on a premium square THEN THE System SHALL apply the premium to the word but not to the blank's zero value
7. WHEN premium squares are used THEN THE System SHALL only apply them on the turn they are first covered

### Requirement 6: Handle End-Game Conditions Properly

**User Story:** As a game developer, I want the game to end correctly when tiles run out or players cannot continue, so that final scores are calculated according to official rules.

#### Acceptance Criteria

1. WHEN a player uses their last tile and the bag is empty THEN THE System SHALL end the game
2. WHEN the game ends THEN THE System SHALL subtract unplayed tile values from each player's score
3. WHEN a player goes out THEN THE System SHALL add the opponent's unplayed tile values to the player's score
4. WHEN six consecutive scores of zero occur THEN THE System SHALL end the game
5. WHEN the game ends THEN THE System SHALL ensure final scores are non-negative

### Requirement 7: Manage Tile Drawing and Rack State

**User Story:** As a Scrabble player, I want tile drawing to follow official rules, so that the game maintains proper tile distribution and rack management.

#### Acceptance Criteria

1. WHEN a player completes a turn THEN THE System SHALL refill their rack to 7 tiles if possible
2. WHEN the bag has fewer than 7 tiles THEN THE System SHALL draw all remaining tiles
3. WHEN a player exchanges tiles THEN THE System SHALL verify the bag contains at least 7 tiles
4. WHEN a player attempts to exchange with fewer than 7 tiles in the bag THEN THE System SHALL reject the exchange and apply a penalty
5. WHEN tiles are drawn THEN THE System SHALL remove them from the bag
6. WHEN tiles are exchanged THEN THE System SHALL return old tiles to the bag and shuffle before drawing new tiles

### Requirement 8: Implement Move Generation Determinism

**User Story:** As a game developer, I want move generation to be deterministic and reproducible, so that training results are consistent and debugging is possible.

#### Acceptance Criteria

1. WHEN moves are generated for a given board state and rack THEN THE System SHALL produce the same moves in the same order
2. WHEN multiple moves exist for the same position THEN THE System SHALL select the best move deterministically
3. WHEN sorting moves THEN THE System SHALL use a consistent sorting key (word length, alphabetical)
4. WHEN generating moves THEN THE Move_Generator SHALL process candidates in sorted order
5. WHEN the same game state occurs THEN THE System SHALL produce identical legal action lists

### Requirement 9: Track and Report Game State

**User Story:** As a developer debugging the system, I want comprehensive game state tracking, so that I can identify and fix issues in gameplay.

#### Acceptance Criteria

1. WHEN a move is attempted THEN THE System SHALL log the move details (word, position, direction)
2. WHEN a move fails validation THEN THE System SHALL log the reason for failure
3. WHEN a game ends THEN THE System SHALL report final scores, turn count, and end condition
4. WHEN an agent makes repeated invalid attempts THEN THE System SHALL track and report the pattern
5. WHEN the game state is printed THEN THE System SHALL show board, scores, racks, and bag count

### Requirement 10: Implement WSL Execution Environment

**User Story:** As a developer running on Windows, I want to execute all game operations in WSL, so that the Python environment and dependencies work correctly.

#### Acceptance Criteria

1. WHEN running game tests THEN THE System SHALL execute commands using `wsl` prefix
2. WHEN activating the virtual environment THEN THE System SHALL use `source /venv/lib/activate`
3. WHEN running training THEN THE System SHALL execute in the WSL environment
4. WHEN running analysis THEN THE System SHALL execute in the WSL environment
5. WHEN file paths are used THEN THE System SHALL use Unix-style paths compatible with WSL
