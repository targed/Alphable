# Design Document: Scrabble Engine Fixes

## Overview

This design addresses three critical issues in the Scrabble engine: negative scores, move repetition, and invalid word overlaps. The root causes have been identified through analysis of game logs and source code:

1. **Negative Scores**: The current penalty system (-10 points per invalid move) can accumulate without bounds, causing deeply negative scores
2. **Move Repetition**: Agents get stuck attempting the same invalid move repeatedly because the banned actions mechanism doesn't prevent all repetition patterns
3. **Invalid Overlaps**: The engine doesn't validate cross-words formed perpendicular to the main play

The solution involves:

- Implementing score floor constraints to prevent negative scores
- Enhancing move validation to check cross-words
- Improving the banned actions mechanism to break repetition cycles
- Adding proper game state tracking and termination conditions

## Architecture

The Scrabble engine follows a layered architecture:

```
┌─────────────────────────────────────┐
│   OpenSpiel Game Interface          │
│   (ScrabbleGame, ScrabbleState)     │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│   Game Logic Layer                  │
│   - Move validation                 │
│   - Scoring calculation             │
│   - State management                │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│   Move Generation Layer             │
│   (GADDAG, MoveGenerator)           │
└─────────────────────────────────────┘
```

Key components:

- **ScrabbleState**: Manages board state, racks, scores, and turn logic
- **MoveGenerator**: Uses GADDAG to generate valid word placements
- **Validation System**: Checks move legality (connectivity, rack, cross-words)
- **Scoring System**: Calculates points including premiums and bonuses
- **Penalty System**: Applies penalties for invalid moves while maintaining score floors

## Components and Interfaces

### 1. Score Management Component

**Purpose**: Ensure scores never become negative

**Interface**:

```python
def apply_penalty(self, player_idx: int, penalty: float) -> None:
    """Apply penalty to player score, ensuring non-negative result"""
    self.scores[player_idx] = max(0.0, self.scores[player_idx] - penalty)

def adjust_final_scores(self) -> None:
    """Apply end-game adjustments per official rules"""
    # Subtract unplayed tile values
    # Add opponent's unplayed tiles if player went out
    # Ensure both scores remain non-negative
```

**Implementation Notes**:

- All score modifications must use `max(0.0, score)` to enforce floor
- Penalties should be proportional (5-10 points) rather than fixed
- Final score calculation follows official Scrabble rules

### 2. Cross-Word Validation Component

**Purpose**: Validate all words formed perpendicular to the main play

**Interface**:

```python
def find_cross_words(self, row: int, col: int, word: str, direction: str) -> List[Tuple[str, int, int, str]]:
    """Find all cross-words formed by placing word at position"""
    # Returns list of (cross_word, start_row, start_col, cross_direction)

def validate_cross_words(self, cross_words: List[Tuple]) -> bool:
    """Check if all cross-words are in dictionary"""
    # Returns True if all cross-words are valid
```

**Implementation Notes**:

- For each tile placed on an empty square, scan perpendicular direction
- Check if adjacent tiles exist above/below (for across) or left/right (for down)
- Extract the full cross-word including the new tile
- Validate each cross-word using GADDAG's fast word check
- Single-letter "words" are not considered cross-words

### 3. Move Repetition Prevention Component

**Purpose**: Detect and break cycles of repeated invalid moves

**Interface**:

```python
def track_failed_action(self, action_id: int) -> bool:
    """Track failed action, return True if should force pass"""
    self.banned_actions.add(action_id)
    return len(self.banned_actions) >= 3

def reset_banned_actions(self) -> None:
    """Clear banned actions for new turn"""
    self.banned_actions = set()
```

**Implementation Notes**:

- Maintain `banned_actions` set per turn
- After 3 failed attempts, force pass (action 450)
- Clear banned actions when turn changes or successful move made
- Track consecutive passes to detect stalemate (4 passes = game over)

### 4. Game Termination Component

**Purpose**: Detect and handle various end-game conditions

**Interface**:

```python
def check_termination_conditions(self) -> bool:
    """Check if game should end"""
    # Returns True if any termination condition met

def get_termination_reason(self) -> str:
    """Get reason for game termination"""
    # Returns human-readable termination reason
```

**Termination Conditions**:

1. Player uses last tile and bag is empty
2. Four consecutive passes (2 per player)
3. Turn count exceeds 100 (hard limit)
4. Turn count > 20 and total score is 0 (mercy rule)
5. Six consecutive zero scores

### 5. Deterministic Move Generation Component

**Purpose**: Ensure consistent move ordering for reproducibility

**Interface**:

```python
def generate_deterministic_moves(self, board: List[List[str]], rack: List[str]) -> List[Dict]:
    """Generate moves in deterministic order"""
    # Returns sorted list of move dictionaries
```

**Implementation Notes**:

- Sort candidates alphabetically during GADDAG traversal
- Use consistent tie-breaking: (-word_length, word_alphabetical)
- Ensure GADDAG traversal order is deterministic
- Map moves to action IDs consistently

## Data Models

### Board State

```python
board: List[List[str]]  # 15x15 grid, '.' for empty, 'A'-'Z' for tiles
```

### Player State

```python
scores: List[float]  # [player0_score, player1_score]
racks: List[List[str]]  # [player0_rack, player1_rack]
```

### Game State

```python
bag: List[str]  # Remaining tiles
turn_count: int  # Number of turns played
consecutive_passes: int  # Count of consecutive passes
banned_actions: Set[int]  # Actions that failed validation this turn
_game_over: bool  # Game termination flag
_current_player: int  # 0 or 1
```

### Move Representation

```python
{
    'row': int,  # Starting row (0-14)
    'col': int,  # Starting column (0-14)
    'word': str,  # Word to place
    'dir': str,  # 'Across' or 'Down'
}
```

### Action ID Mapping

```python
action_id = (row * 15 + col) * 2 + direction
# where direction: 0 = Across, 1 = Down
# Special actions: 450 = Pass, 451 = Exchange
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Score Non-Negativity

_For any_ game state at any point during or after the game, both player scores should be greater than or equal to zero.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 6.5**

### Property 2: Move Repetition Prevention

_For any_ turn where an agent attempts the same invalid action three times, the system should force a pass and clear the banned actions for the next turn.

**Validates: Requirements 2.1, 2.5, 2.6**

### Property 3: Game Termination Bounds

_For any_ game, the turn count should not exceed 100, and if turn count exceeds 20 with zero total score, the game should terminate.

**Validates: Requirements 2.2, 2.4**

### Property 4: Consecutive Pass Termination

_For any_ sequence of four consecutive passes (two per player), the game should terminate.

**Validates: Requirements 2.3, 6.4**

### Property 5: Board Connectivity

_For any_ valid move after the first move, at least one tile in the played word should be adjacent to an existing tile on the board.

**Validates: Requirements 3.1, 3.6**

### Property 6: First Move Center Coverage

_For any_ first move, the word should cover the center square at position (7, 7).

**Validates: Requirements 3.2**

### Property 7: Boundary Compliance

_For any_ valid move, all tiles should be placed within board boundaries (row and column both in range 0-14).

**Validates: Requirements 3.3**

### Property 8: Rack Availability

_For any_ valid move, the player should have all required tiles in their rack (accounting for blanks as wildcards).

**Validates: Requirements 3.4**

### Property 9: Tile Matching

_For any_ valid move that uses existing board tiles, the word should match those tiles exactly at their positions.

**Validates: Requirements 3.5**

### Property 10: Cross-Word Validity

_For any_ valid move that forms cross-words, all cross-words should be present in the dictionary.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 11: Cross-Word Scoring

_For any_ move that forms valid cross-words, the turn score should include points for all cross-words.

**Validates: Requirements 4.4, 5.5**

### Property 12: Premium Square Application

_For any_ move using premium squares, letter multipliers should be applied before word multipliers.

**Validates: Requirements 5.2, 5.3**

### Property 13: Bingo Bonus

_For any_ move that uses all 7 tiles from the rack, the score should include a 50-point bonus.

**Validates: Requirements 5.4**

### Property 14: Premium Square Single Use

_For any_ premium square, the multiplier should only apply on the turn when it is first covered.

**Validates: Requirements 5.7**

### Property 15: Rack Refill

_For any_ completed turn where the bag is not empty, the player's rack should be refilled to 7 tiles (or all remaining tiles if fewer than 7).

**Validates: Requirements 7.1, 7.2**

### Property 16: Exchange Validation

_For any_ exchange attempt, the bag should contain at least 7 tiles, otherwise the exchange should be rejected.

**Validates: Requirements 7.3, 7.4**

### Property 17: Deterministic Move Generation

_For any_ board state and rack combination, generating moves twice should produce identical move lists in identical order.

**Validates: Requirements 8.1, 8.5**

### Property 18: Deterministic Move Selection

_For any_ position with multiple possible words, the system should select the same word deterministically based on length and alphabetical order.

**Validates: Requirements 8.2, 8.3, 8.4**

### Property 19: End-Game Tile Adjustment

_For any_ completed game, the final scores should reflect unplayed tile values subtracted from each player's score.

**Validates: Requirements 6.2**

### Property 20: Out Bonus

_For any_ game where one player uses their last tile, that player's score should include the sum of the opponent's unplayed tile values.

**Validates: Requirements 6.3**

## Error Handling

### Invalid Move Handling

- **Detection**: Validate moves before applying to board
- **Response**: Apply penalty (5-10 points), ban action, track attempt count
- **Recovery**: Force pass after 3 attempts, clear bans on turn change

### Cross-Word Validation Failures

- **Detection**: Check all cross-words against dictionary
- **Response**: Reject entire move, apply penalty, ban action
- **Logging**: Record which cross-word(s) were invalid

### Rack Insufficiency

- **Detection**: Check rack contents before move application
- **Response**: Reject move, apply penalty, ban action
- **Prevention**: Move generator should only produce valid moves

### Boundary Violations

- **Detection**: Check coordinates before move application
- **Response**: Reject move, apply penalty, ban action
- **Prevention**: Move generator should respect boundaries

### Stalemate Detection

- **Detection**: Track consecutive passes and zero-score turns
- **Response**: Terminate game, calculate final scores
- **Logging**: Record termination reason

### Score Underflow Prevention

- **Detection**: Check score before applying penalty
- **Response**: Use `max(0.0, score - penalty)` to enforce floor
- **Logging**: Record when score floor is hit

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples and edge cases:

1. **Score Floor Tests**

   - Test penalty application with various starting scores
   - Test score remains at 0 when multiple penalties applied
   - Test final score calculation with negative intermediate values

2. **Cross-Word Validation Tests**

   - Test single cross-word detection and validation
   - Test multiple cross-words in one move
   - Test cross-word scoring with premiums
   - Test rejection of invalid cross-words

3. **Move Repetition Tests**

   - Test banned actions accumulation
   - Test forced pass after 3 attempts
   - Test banned actions reset on turn change

4. **Termination Tests**

   - Test each termination condition independently
   - Test termination reason reporting
   - Test final score calculation at termination

5. **Edge Cases**
   - Empty bag scenarios
   - First move validation
   - Premium square edge cases
   - Blank tile handling

### Property-Based Tests

Property-based tests will verify universal properties across randomized inputs using a Python PBT library (e.g., Hypothesis):

**Configuration**: Each property test should run a minimum of 100 iterations.

**Test Tagging**: Each test must reference its design property:

```python
# Feature: scrabble-engine-fixes, Property 1: Score Non-Negativity
```

**Property Test Examples**:

1. **Property 1: Score Non-Negativity**

   - Generate random game states with various scores
   - Apply random penalties
   - Assert both scores >= 0

2. **Property 5: Board Connectivity**

   - Generate random board states with tiles
   - Generate random valid moves
   - Assert each move connects to existing tiles

3. **Property 10: Cross-Word Validity**

   - Generate random moves that form cross-words
   - Validate all cross-words
   - Assert all are in dictionary or move is rejected

4. **Property 17: Deterministic Move Generation**
   - Generate random board and rack states
   - Generate moves twice
   - Assert move lists are identical

### Integration Tests

Integration tests will verify end-to-end gameplay:

1. **Full Game Simulation**

   - Play complete games with random agents
   - Verify no negative scores occur
   - Verify games terminate properly
   - Verify final scores follow official rules

2. **AlphaZero Training Integration**
   - Run short training sessions
   - Verify no crashes or infinite loops
   - Verify game logs show proper progression
   - Verify score distributions are reasonable

### Test Execution Environment

All tests must be executed in WSL:

```bash
wsl
source /venv/lib/activate
python -m pytest tests/
```

## Implementation Notes

### WSL Execution Context

All commands must be executed in Windows Subsystem for Linux:

- Prefix all commands with `wsl`
- Activate virtual environment: `source /venv/lib/activate`
- Use Unix-style paths
- Ensure Python dependencies are installed in WSL environment

### Performance Considerations

- Cross-word validation adds overhead to move validation
- Use GADDAG's fast word check (O(word_length))
- Cache cross-check sets during move generation
- Avoid redundant dictionary lookups

### Backward Compatibility

- Maintain OpenSpiel interface compatibility
- Preserve existing action ID mapping
- Keep observation tensor format unchanged
- Maintain checkpoint compatibility where possible

### Debugging Support

- Add comprehensive logging for move validation failures
- Track and report repetition patterns
- Log termination reasons
- Include game state in error messages

## References

- NASPA Official Tournament Rules (December 2016): `resources/rules-20161201.pdf`
- OpenSpiel Documentation: `resources/openspiel-readthedocs-io-en-latest.pdf`
- Current Implementation: `scrabble.py`, `structure.py`
- Training Configuration: `train.py`
- Game Logs: `data/resultsv1/result_*.txt`
