---
inclusion: fileMatch
fileMatchPattern: "scrabble.py|test_*.py|*test*.py"
---

# Scrabble Rules Compliance Standards

## Critical Rule Implementation Requirements

When working with the Scrabble engine or tests, ensure strict compliance with these official NASPA rules:

### Board and Placement Rules
- **First Move**: Must cover center square (7,7) with Double Word bonus
- **Connectivity**: All subsequent moves must connect to existing tiles
- **Direction**: Words must be horizontal or vertical only (no diagonals)
- **Boundaries**: All tiles must be within 0-14 grid coordinates

### Word Validation (6-Step Process)
1. **Rack Validation**: Player must possess all required tiles
2. **Boundary Check**: All placements within board limits
3. **Connectivity**: New tiles connect to existing board
4. **Dictionary Check**: Main word exists in NWL2023 lexicon
5. **Cross-Word Validation**: All perpendicular words are valid
6. **Adjacent Word Validation**: All same-direction adjacent words are valid

### Scoring Rules
- **Premium Squares**: Apply only on first use (track with `used_premiums`)
- **Letter Bonuses**: Applied before word bonuses
- **Word Bonuses**: Can compound (TW + TW = 9x multiplier)
- **Bingo Bonus**: +50 points for using all 7 tiles
- **Score Floor**: Scores must never be negative

### Game Flow
- **Exchanges**: Forbidden when bag has <7 tiles
- **Passes**: Count toward termination (4 consecutive = game end)
- **Endgame**: When bag empty + one player out, adjust scores by remaining tiles

## Testing Standards

### Required Test Coverage
- Unit tests for each validation step
- Integration tests with real game scenarios
- Edge case testing (boundaries, premium squares, endgame)
- Performance benchmarks for move generation

### Test Naming Convention
- `test_[feature].py` for unit tests
- `test_integration_[scenario].py` for integration tests
- `verify_[requirement].py` for compliance verification

### Critical Test Cases
- Adjacent word formation (BOXERS + JOES ≠ BOXERSJOES)
- Premium square single-use enforcement
- Cross-word validation in all directions
- Endgame scoring adjustments
- Invalid move rejection without state corruption

## Performance Requirements
- Move generation: <10ms for typical positions
- Full game simulation: <1 second
- Memory usage: Efficient board representation
- Deterministic: Same input → same output order

## Error Handling
- Invalid moves should be rejected cleanly
- Game state must remain consistent after failed moves
- Clear error messages for debugging
- No crashes on malformed input